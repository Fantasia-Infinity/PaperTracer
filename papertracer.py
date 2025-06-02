"""
Google Scholar 引用爬虫
递归爬取文章的引用关系并返回树形数据结构
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import re
from urllib.parse import urljoin, parse_qs, urlparse
from dataclasses import dataclass
from typing import List, Dict, Optional, Set
import json
import logging
import platform
from pathlib import Path
from tempfile import NamedTemporaryFile
import traceback
import pickle
from datetime import datetime, timedelta

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 尝试导入无头浏览器相关依赖（可选的，用于处理CAPTCHA）
BROWSER_AVAILABLE = False
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    BROWSER_AVAILABLE = True
    logger.info("浏览器模块已加载，可用于处理CAPTCHA")
except ImportError:
    logger.warning("浏览器模块导入失败，无法使用浏览器绕过CAPTCHA。考虑安装: pip install undetected-chromedriver selenium")

@dataclass
class Paper:
    """论文数据结构"""
    title: str
    authors: str = ""
    year: str = ""
    citation_count: int = 0
    url: str = ""
    cited_by_url: str = ""
    abstract: str = ""

@dataclass 
class CitationNode:
    """引用树节点"""
    paper: Paper
    children: List['CitationNode']
    depth: int = 0

class GoogleScholarCrawler:
    """Google Scholar 爬虫类"""
    
    def __init__(self, max_depth=3, max_papers_per_level=10, delay_range=(2, 5), max_captcha_retries=3,
                 use_browser_fallback=True, captcha_service_api_key=None, proxy_list=None, skip_429_errors=False):
        self.max_depth = max_depth
        self.max_papers_per_level = max_papers_per_level
        self.delay_range = delay_range
        self.max_captcha_retries = max_captcha_retries
        self.use_browser_fallback = use_browser_fallback and BROWSER_AVAILABLE
        self.use_headless_browser = True  # 添加缺失的属性
        self.captcha_service_api_key = captcha_service_api_key
        self.proxy_list = proxy_list or []
        self.skip_429_errors = skip_429_errors  # 新增: 是否跳过429错误
        self.proxy_index = 0
        self.current_proxy = self.proxy_list[0] if self.proxy_list else None
        self.visited_urls: Set[str] = set()
        self.session = requests.Session()
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
        ]
        self.request_count = 0
        self.browser = None
        
        # Session persistence
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.last_429_time = None
        self.consecutive_429_count = 0
        
        # 设置更完整的请求头
        self._update_headers()

    def _get_random_delay(self):
        """获取随机延迟时间（已废弃，使用_adaptive_delay代替）"""
        return random.uniform(*self.delay_range)
    
    def _extract_cluster_id(self, url: str) -> Optional[str]:
        """从URL中提取cluster ID"""
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            if 'cites' in params:
                return params['cites'][0]
            elif 'cluster' in params:
                return params['cluster'][0]
        except:
            pass
        return None
    
    def _parse_paper_info(self, result_div) -> Paper:
        """解析单篇论文信息"""
        try:
            # 提取标题 - 尝试多种选择器
            title_elem = (result_div.find('h3', class_='gs_rt') or 
                         result_div.find('h3') or 
                         result_div.find('a', class_='gs_rt'))
            
            if title_elem:
                # 如果标题在链接内，提取链接文本
                title_link = title_elem.find('a') if title_elem.name != 'a' else title_elem
                if title_link:
                    title = title_link.get_text(strip=True)
                else:
                    title = title_elem.get_text(strip=True)
            else:
                title = "Unknown Title"
            
            # 过滤掉明显的错误标题
            if not title or title.lower() in ['unknown title', 'parse error', '']:
                logger.debug("发现空标题或错误标题，跳过")
                return Paper(title="Parse Error", authors="", year="")
            
            # 提取作者和年份
            authors_elem = result_div.find('div', class_='gs_a')
            authors_text = authors_elem.get_text(strip=True) if authors_elem else ""
            
            # 尝试提取年份
            year_match = re.search(r'\b(19|20)\d{2}\b', authors_text)
            year = year_match.group() if year_match else ""
            
            # 提取作者（年份前的部分）
            if year:
                authors = authors_text.split(year)[0].strip(' -,')
            else:
                authors = authors_text
            
            # 清理作者信息
            authors = re.sub(r'\s*-\s*$', '', authors)  # 移除末尾的破折号
            authors = re.sub(r'\s+', ' ', authors)  # 标准化空格
            
            # 提取引用次数
            cite_elem = result_div.find('a', string=re.compile(r'Cited by \d+', re.IGNORECASE))
            if not cite_elem:
                # 尝试其他可能的引用链接格式
                cite_elem = result_div.find('a', href=re.compile(r'cites='))
            
            citation_count = 0
            cited_by_url = ""
            
            if cite_elem:
                cite_text = cite_elem.get_text(strip=True)
                cite_match = re.search(r'Cited by (\d+)', cite_text, re.IGNORECASE)
                if cite_match:
                    citation_count = int(cite_match.group(1))
                    cited_by_url = urljoin('https://scholar.google.com', cite_elem.get('href', ''))
            
            # 提取论文URL
            paper_url = ""
            if title_elem:
                link_elem = title_elem.find('a') if title_elem.name != 'a' else title_elem
                if link_elem:
                    paper_url = link_elem.get('href', '')
            
            # 提取摘要
            abstract_elem = result_div.find('span', class_='gs_rs')
            abstract = abstract_elem.get_text(strip=True) if abstract_elem else ""
            
            paper = Paper(
                title=title,
                authors=authors,
                year=year,
                citation_count=citation_count,
                url=paper_url,
                cited_by_url=cited_by_url,
                abstract=abstract
            )
            
            logger.debug(f"解析论文成功: {title[:50]}...")
            return paper
        
        except Exception as e:
            logger.error(f"解析论文信息时出错: {e}")
            return Paper(title="Parse Error", authors="", year="")
    
    def _make_request(self, url: str, timeout: int = 20) -> Optional[requests.Response]:
        """统一的请求方法，自动选择ScrapingAnt代理池或常规请求"""
        # 常规请求方法
        self._adaptive_delay()
        
        if self.request_count % 5 == 0:
            self._update_headers()
        
        response = self.session.get(url, timeout=timeout)
        response.raise_for_status()
        return response

    def _fetch_citations(self, cited_by_url: str) -> List[Paper]:
        """获取引用该论文的文章列表"""
        if not cited_by_url or cited_by_url in self.visited_urls:
            return []
        
        self.visited_urls.add(cited_by_url)  # Mark as visited once we start processing it
        
        attempt = 0
        browser_attempt = False  # 标记是否已尝试使用浏览器
        
        while attempt < self.max_captcha_retries:
            try:
                logger.info(f"正在爬取: {cited_by_url} (尝试 {attempt + 1}/{self.max_captcha_retries})")
                
                # 使用浏览器fallback尝试绕过CAPTCHA
                if browser_attempt and self.use_browser_fallback:
                    logger.info("尝试使用浏览器方式绕过CAPTCHA...")
                    html_content = self._fetch_with_browser(cited_by_url)
                    if html_content:
                        soup = BeautifulSoup(html_content, 'html.parser')
                    else:
                        logger.warning("浏览器获取内容失败，返回空结果")
                        return []
                else:
                    # 常规请求方法
                    self._adaptive_delay()
                    
                    if self.request_count % 5 == 0:
                        self._update_headers()
                    
                    response = self.session.get(cited_by_url, timeout=20)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                
                # 检测CAPTCHA或封禁
                if self._is_captcha_page(soup):
                    logger.warning(f"CAPTCHA 检测于: {cited_by_url} (尝试 {attempt + 1})")
                    
                    # 执行CAPTCHA处理策略
                    logger.info("🔄 执行CAPTCHA处理策略...")
                    
                    # 1. 更新请求头和增加随机性
                    self._update_headers()
                    logger.info("   ✓ 已更新请求头")
                    
                    # 2. 使用渐进式延迟策略
                    retry_delay = 2 + attempt * 2 + random.uniform(1, 3)
                    logger.info(f"   ✓ 执行渐进式延迟重试: {retry_delay:.1f} 秒")
                    time.sleep(retry_delay)
                    
                    # 3. 如果启用了429跳过模式，不使用浏览器处理但继续尝试自动策略
                    if self.skip_429_errors:
                        # 添加额外随机延迟以增加下次成功概率
                        if attempt > 0:
                            extra_delay = random.uniform(3, 8)
                            logger.info(f"   ✓ 执行额外延迟: {extra_delay:.1f} 秒")
                            time.sleep(extra_delay)
                            
                        logger.info("⏭️  跳过模式已启用，跳过浏览器CAPTCHA处理")
                        logger.info("   ✓ 已执行所有自动化策略，继续尝试")
                        attempt += 1
                        continue  # 继续下一次尝试
                    
                    # 4. 默认模式：如果还没尝试过浏览器方法，且配置允许，则尝试浏览器方法
                    if not browser_attempt and self.use_browser_fallback:
                        logger.info("检测到CAPTCHA，切换到浏览器方式尝试...")
                        browser_attempt = True
                        # 不增加尝试次数，直接进入下一循环用浏览器访问
                        continue
                    
                    # 已经尝试过浏览器或不允许使用浏览器，则处理CAPTCHA
                    self._handle_captcha_or_block(cited_by_url, response.text if 'response' in locals() else "", attempt)
                    attempt += 1
                    
                    if attempt >= self.max_captcha_retries:
                        logger.error(f"CAPTCHA 验证失败次数过多，放弃爬取: {cited_by_url}")
                        return []
                    
                    logger.info(f"CAPTCHA 后等待后重试 ({attempt + 1}/{self.max_captcha_retries}): {cited_by_url}")
                    browser_attempt = False  # 重置浏览器尝试状态，再次从常规请求开始
                    continue
                
                # 查找所有论文结果
                paper_divs = soup.find_all('div', class_='gs_r')
                
                # 如果没有找到结果，可能是页面结构发生了变化
                if not paper_divs:
                    logger.warning(f"未找到论文结果，可能页面结构已变化: {cited_by_url}")
                    # 尝试其他可能的选择器
                    paper_divs = soup.find_all('div', class_='gs_ri') or soup.find_all('div', {'data-lid': True})
                
                papers = []
                
                for div in paper_divs[:self.max_papers_per_level]:
                    paper = self._parse_paper_info(div)
                    if paper.title != "Parse Error" and paper.title != "Unknown Title":
                        papers.append(paper)
                
                # 按引用次数排序（降序），引用次数高的论文优先
                papers.sort(key=lambda p: p.citation_count, reverse=True)
                logger.info(f"找到 {len(papers)} 篇有效引用论文，已按引用量排序 from {cited_by_url}")
                if papers:
                    logger.info(f"引用量范围: {papers[0].citation_count} 到 {papers[-1].citation_count}")
                
                # 成功请求，重置429跟踪
                self._reset_429_tracking()
                
                # 如果没有找到任何有效论文，记录调试信息
                if not papers and paper_divs:
                    debug_file = f"debug_no_papers_{int(time.time())}.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(soup.prettify())
                    logger.warning(f"解析成功但未提取到论文，已保存调试页面到: {debug_file}")
                
                return papers  # Success
            
            except requests.exceptions.RequestException as e:
                error_msg = str(e)
                logger.error(f"网络请求失败 ({cited_by_url}): {error_msg} (尝试 {attempt + 1}/{self.max_captcha_retries})")
                
                # 特殊处理429错误 - Too Many Requests
                if "429" in error_msg or "Too Many Requests" in error_msg:
                    result = self._handle_429_error(cited_by_url)
                    if result:  # 如果手动验证成功，使用返回的页面内容
                        soup = BeautifulSoup(result, 'html.parser')
                        # 继续正常的页面解析流程
                        break  # 跳出异常处理循环，使用获得的页面内容
                    else:
                        # 手动验证失败，继续原有逻辑
                        pass
                else:
                    # 成功请求，重置429跟踪
                    self._reset_429_tracking()
                
                attempt += 1
                
                # 如果是网络错误且未尝试过浏览器，切换到浏览器模式尝试
                if not browser_attempt and self.use_browser_fallback:
                    logger.info("网络请求失败，切换到浏览器方式尝试...")
                    browser_attempt = True
                    continue
                
                if attempt >= self.max_captcha_retries:
                    logger.error(f"网络请求失败次数过多，放弃爬取: {cited_by_url}")
                    return []
                    
                # 对于非429错误，使用标准延迟
                if "429" not in error_msg and "Too Many Requests" not in error_msg:
                    time.sleep(random.uniform(3, 7) * (attempt + 1))
                browser_attempt = False  # 重置浏览器尝试状态
                continue
                
            except Exception as e:
                logger.error(f"解析页面时发生未知错误 ({cited_by_url}): {e} (尝试 {attempt + 1}/{self.max_captcha_retries})")
                # 保存调试 HTML for unexpected errors during parsing
                if 'response' in locals() and hasattr(response, 'text'):
                    debug_file = f"debug_parse_error_{int(time.time())}.html"
                    try:
                        with open(debug_file, 'w', encoding='utf-8') as f:
                            f.write(response.text)
                        logger.warning(f"未知解析错误，已保存调试页面到: {debug_file}")
                    except Exception as e_debug:
                        logger.error(f"保存调试页面失败: {e_debug}")
                
                attempt += 1
                if attempt >= self.max_captcha_retries:
                    logger.error(f"未知错误次数过多，放弃爬取: {cited_by_url}")
                    return []
                time.sleep(random.uniform(3, 7) * (attempt + 1))
                browser_attempt = False  # 重置浏览器尝试状态
                continue
        
        logger.error(f"所有尝试均失败: {cited_by_url}")
        return []

    def _get_paper_from_scholar_url(self, scholar_url: str) -> Optional[Paper]:
        """从Scholar搜索URL获取原始论文信息"""
        attempt = 0
        browser_attempt = False  # 标记是否已尝试使用浏览器
        
        while attempt < self.max_captcha_retries:
            try:
                logger.info(f"获取原始论文信息: {scholar_url} (尝试 {attempt + 1}/{self.max_captcha_retries})")
                
                # 使用浏览器fallback尝试绕过CAPTCHA
                if browser_attempt and self.use_browser_fallback:
                    logger.info("尝试使用浏览器方式绕过CAPTCHA...")
                    html_content = self._fetch_with_browser(scholar_url)
                    if html_content:
                        soup = BeautifulSoup(html_content, 'html.parser')
                    else:
                        logger.warning("浏览器获取内容失败，返回None")
                        return None
                else:
                    # 常规请求方法
                    self._adaptive_delay()
                    
                    if self.request_count % 5 == 0:
                        self._update_headers()
                    
                    response = self.session.get(scholar_url, timeout=20)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                
                # 检测CAPTCHA或封禁
                if self._is_captcha_page(soup):
                    logger.warning(f"CAPTCHA 检测于获取原始论文: {scholar_url} (尝试 {attempt + 1})")
                    
                    # 执行CAPTCHA处理策略
                    logger.info("🔄 执行CAPTCHA处理策略...")
                    
                    # 1. 更新请求头和增加随机性
                    self._update_headers()
                    logger.info("   ✓ 已更新请求头")
                    
                    # 2. 使用渐进式延迟策略
                    retry_delay = 2 + attempt * 2 + random.uniform(1, 3)
                    logger.info(f"   ✓ 执行渐进式延迟重试: {retry_delay:.1f} 秒")
                    time.sleep(retry_delay)
                    
                    # 3. 如果启用了429跳过模式，不使用浏览器处理但继续尝试自动策略
                    if self.skip_429_errors:
                        # 添加额外随机延迟以增加下次成功概率
                        if attempt > 0:
                            extra_delay = random.uniform(3, 8)
                            logger.info(f"   ✓ 执行额外延迟: {extra_delay:.1f} 秒")
                            time.sleep(extra_delay)
                            
                        logger.info("⏭️  跳过模式已启用，跳过浏览器CAPTCHA处理")
                        logger.info("   ✓ 已执行所有自动化策略，继续尝试")
                        attempt += 1
                        continue  # 继续下一次尝试
                    
                    # 4. 默认模式：如果还没尝试过浏览器方法，且配置允许，则尝试浏览器方法
                    if not browser_attempt and self.use_browser_fallback:
                        logger.info("检测到CAPTCHA，切换到浏览器方式尝试...")
                        browser_attempt = True
                        # 不增加尝试次数，直接进入下一循环用浏览器访问
                        continue
                    
                    # 已经尝试过浏览器或不允许使用浏览器，则处理CAPTCHA
                    self._handle_captcha_or_block(scholar_url, response.text if 'response' in locals() else "", attempt)
                    attempt += 1
                    
                    if attempt >= self.max_captcha_retries:
                        logger.error(f"CAPTCHA 验证失败次数过多，放弃获取原始论文: {scholar_url}")
                        return None
                    
                    logger.info(f"CAPTCHA 后等待后重试 ({attempt + 1}/{self.max_captcha_retries}): {scholar_url}")
                    browser_attempt = False  # 重置浏览器尝试状态，再次从常规请求开始
                    continue
                
                # 查找第一个搜索结果
                first_result = soup.find('div', class_='gs_r')
                if not first_result:
                    # 尝试其他可能的选择器
                    first_result = soup.find('div', class_='gs_ri') or soup.find('div', {'data-lid': True})
                
                if first_result:
                    return self._parse_paper_info(first_result)
                else:
                    logger.warning(f"未找到搜索结果 for {scholar_url}")
                    # 如果是浏览器方式获取的结果，保存页面进行调试
                    if browser_attempt:
                        debug_file = f"debug_browser_no_results_{int(time.time())}.html"
                        with open(debug_file, 'w', encoding='utf-8') as f:
                            f.write(soup.prettify())
                        logger.warning(f"浏览器获取页面无结果，已保存调试页面到: {debug_file}")
                    
                    # 如果页面加载成功但没有结果，可能是真的找不到
                    return None
            
            except requests.exceptions.RequestException as e:
                error_msg = str(e)
                logger.error(f"网络请求失败获取原始论文 ({scholar_url}): {error_msg} (尝试 {attempt + 1}/{self.max_captcha_retries})")
                
                # 特殊处理429错误 - Too Many Requests
                if "429" in error_msg or "Too Many Requests" in error_msg:
                    result = self._handle_429_error(scholar_url)
                    if result:  # 如果手动验证成功，使用返回的页面内容
                        soup = BeautifulSoup(result, 'html.parser')
                        # 继续正常的页面解析流程
                        break  # 跳出异常处理循环，使用获得的页面内容
                    else:
                        # 手动验证失败，继续原有逻辑
                        pass
                else:
                    # 成功请求，重置429跟踪
                    self._reset_429_tracking()
                
                attempt += 1
                
                # 如果是网络错误且未尝试过浏览器，切换到浏览器模式尝试
                if not browser_attempt and self.use_browser_fallback:
                    logger.info("网络请求失败，切换到浏览器方式尝试...")
                    browser_attempt = True
                    continue
                
                if attempt >= self.max_captcha_retries:
                    logger.error(f"网络请求失败次数过多，放弃获取原始论文: {scholar_url}")
                    return None
                
                # 对于非429错误，使用标准延迟
                if "429" not in error_msg and "Too Many Requests" not in error_msg:
                    time.sleep(random.uniform(3, 7) * (attempt + 1))
                browser_attempt = False  # 重置浏览器尝试状态
                continue
                
            except Exception as e:
                logger.error(f"获取原始论文信息时发生未知错误 ({scholar_url}): {e} (尝试 {attempt + 1}/{self.max_captcha_retries})")
                if 'response' in locals() and hasattr(response, 'text'):
                    debug_file = f"debug_get_paper_error_{int(time.time())}.html"
                    try:
                        with open(debug_file, 'w', encoding='utf-8') as f:
                            f.write(response.text)
                        logger.warning(f"未知错误获取原始论文，已保存调试页面到: {debug_file}")
                    except Exception as e_debug:
                        logger.error(f"保存调试页面失败: {e_debug}")
                
                attempt += 1
                if attempt >= self.max_captcha_retries:
                    logger.error(f"未知错误次数过多，放弃获取原始论文: {scholar_url}")
                    return None
                
                time.sleep(random.uniform(3, 7) * (attempt + 1))
                browser_attempt = False  # 重置浏览器尝试状态
                continue
        
        logger.error(f"所有尝试均失败获取原始论文: {scholar_url}")
        return None

    def build_citation_tree(self, start_url: str, current_depth: int = 0) -> Optional[CitationNode]:
        """递归构建引用树"""
        if current_depth >= self.max_depth:
            return None
        
        logger.info(f"构建引用树，深度: {current_depth}")
        
        # 如果是起始URL，需要先获取原始论文信息
        if current_depth == 0:
            if 'cites=' in start_url:
                # 这是一个"被引用"页面，需要获取原始论文信息
                # 构造一个虚拟的根论文
                root_paper = Paper(
                    title="Root Paper (从引用页面开始)",
                    authors="Unknown",
                    year="",
                    citation_count=0,
                    url="",
                    cited_by_url=start_url
                )
            else:
                # 尝试从搜索结果获取论文信息
                root_paper = self._get_paper_from_scholar_url(start_url)
                if not root_paper:
                    logger.error("无法获取起始论文信息")
                    return None
        else:
            # 这种情况在递归调用中不应该发生
            return None
        
        # 创建根节点
        root_node = CitationNode(paper=root_paper, children=[], depth=current_depth)
        
        # 获取引用这篇论文的文章（已在_fetch_citations中按引用量排序）
        citing_papers = self._fetch_citations(root_paper.cited_by_url)
        
        # 为每个引用论文递归构建子树（论文已按引用量降序排列）
        for citing_paper in citing_papers:
            if citing_paper.cited_by_url and current_depth + 1 < self.max_depth:
                child_node = self._build_citation_subtree(citing_paper, current_depth + 1)
                if child_node:
                    root_node.children.append(child_node)
            else:
                # 叶子节点
                leaf_node = CitationNode(paper=citing_paper, children=[], depth=current_depth + 1)
                root_node.children.append(leaf_node)
        
        return root_node
    
    def _build_citation_subtree(self, paper: Paper, depth: int) -> Optional[CitationNode]:
        """递归构建引用子树"""
        if depth >= self.max_depth:
            return None
        
        node = CitationNode(paper=paper, children=[], depth=depth)
        
        # 获取引用这篇论文的文章（已在_fetch_citations中按引用量排序）
        citing_papers = self._fetch_citations(paper.cited_by_url)
        
        # 为每个引用论文递归构建子树（论文已按引用量降序排列）
        for citing_paper in citing_papers:
            if citing_paper.cited_by_url and depth + 1 < self.max_depth:
                child_node = self._build_citation_subtree(citing_paper, depth + 1)
                if child_node:
                    node.children.append(child_node)
            else:
                # 叶子节点
                leaf_node = CitationNode(paper=citing_paper, children=[], depth=depth + 1)
                node.children.append(leaf_node)
        
        return node

    def _update_headers(self):
        """更新请求头，模拟真实浏览器"""
        user_agent = random.choice(self.user_agents)
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        
    def _rotate_proxy(self):
        """轮换代理服务器"""
        if not self.proxy_list:
            return
            
        self.proxy_index = (self.proxy_index + 1) % len(self.proxy_list)
        self.current_proxy = self.proxy_list[self.proxy_index]
        logger.info(f"轮换代理到: {self.current_proxy}")
        
        # 更新session代理
        if self.current_proxy:
            if self.current_proxy.startswith('http'):
                self.session.proxies = {
                    'http': self.current_proxy,
                    'https': self.current_proxy
                }
            else:
                self.session.proxies = {
                    'http': f'socks5://{self.current_proxy}',
                    'https': f'socks5://{self.current_proxy}'
                }
                
        # 更新浏览器代理（如果浏览器已初始化）
        if self.browser:
            try:
                logger.info("正在关闭浏览器以应用新代理...")
                self.browser.quit()
                self.browser = None
                logger.info("浏览器已关闭，将在下次请求时重新初始化")
            except Exception as e:
                logger.error(f"关闭浏览器时出错: {e}")
    
    def _is_captcha_page(self, soup: BeautifulSoup) -> bool:
        """检测是否遇到了CAPTCHA页面"""
        captcha_indicators = [
            'please show you\'re not a robot',
            'captcha',
            'recaptcha',
            'robot',
            'verify you are human',
            'unusual traffic'
        ]
        
        page_text = soup.get_text().lower()
        for indicator in captcha_indicators:
            if indicator in page_text:
                return True
        
        # 检查是否有reCAPTCHA相关的元素
        if soup.find('div', {'class': 'g-recaptcha'}):
            return True
        if soup.find('iframe', src=lambda x: x and 'recaptcha' in x):
            return True
            
        # Additional indicators for CAPTCHA
        additional_indicators = [
            'unusual traffic from your network',
            'automated requests from your computer',
            'network is sending automated queries'
        ]
        for indicator in additional_indicators:
            if indicator in page_text:
                return True
                
        return False
    
    def _fetch_with_browser(self, url: str) -> Optional[str]:
        """使用浏览器获取页面内容，可处理CAPTCHA"""
        if not BROWSER_AVAILABLE:
            logger.error("浏览器模块不可用，无法使用浏览器方式")
            return None
        
        try:
            # 初始化浏览器（如果还没有）
            if not self.browser:
                self._init_browser()
            
            if not self.browser:
                logger.error("浏览器初始化失败")
                return None
            
            logger.info(f"使用浏览器访问: {url}")
            self.browser.get(url)
            
            # 等待页面加载
            time.sleep(3)
            
            # 检查是否遇到CAPTCHA或429错误
            page_source = self.browser.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 检查429错误或CAPTCHA
            page_text = soup.get_text().lower()
            if ('429' in page_text or 'too many requests' in page_text or 
                'unusual traffic' in page_text or 'sorry' in soup.title.string.lower() if soup.title else False):
                logger.warning("检测到429错误页面")
                if self.skip_429_errors:
                    # 在跳过模式下，仍尝试一些基本的自动化策略
                    logger.info("⏭️  智能跳过模式已启用，执行自动化策略...")
                    
                    # 尝试切换User-Agent
                    self._update_headers()
                    logger.info("   ✓ 已更新User-Agent")
                    
                    # 短暂延迟后返回当前页面内容作为最佳尝试
                    retry_delay = random.uniform(2, 5)
                    logger.info(f"   ✓ 执行延迟: {retry_delay:.1f} 秒")
                    time.sleep(retry_delay)
                    
                    logger.info("   ✓ 已执行所有自动化策略，返回当前页面内容")
                    return page_source  # 返回当前内容而不是None
                    
                logger.warning("切换到手动处理模式")
                return self._handle_manual_captcha(url)
            
            if self._is_captcha_page(soup):
                logger.warning("检测到CAPTCHA页面")
                if self.skip_429_errors:
                    # 在跳过模式下，仍尝试一些基本的自动化策略
                    logger.info("⏭️  智能跳过模式已启用，执行自动化策略...")
                    
                    # 尝试切换User-Agent
                    self._update_headers()
                    logger.info("   ✓ 已更新User-Agent")
                    
                    # 短暂延迟后返回当前页面内容作为最佳尝试
                    retry_delay = random.uniform(2, 5)
                    logger.info(f"   ✓ 执行延迟: {retry_delay:.1f} 秒")
                    time.sleep(retry_delay)
                    
                    logger.info("   ✓ 已执行所有自动化策略，返回当前页面内容")
                    return page_source  # 返回当前内容而不是None
                
                logger.warning("需要人工处理")
                return self._handle_manual_captcha(url)
            
            return page_source
            
        except Exception as e:
            logger.error(f"浏览器访问失败: {e}")
            return None
    
    def _init_browser(self):
        """初始化无头浏览器"""
        try:
            if not BROWSER_AVAILABLE:
                logger.error("浏览器依赖不可用")
                return
                
            options = uc.ChromeOptions()
            
            # 根据配置决定是否使用无头模式
            if self.use_headless_browser:
                options.add_argument('--headless')
            
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            
            # 兼容性修复：只在支持的Chrome版本中使用excludeSwitches
            try:
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
            except Exception as ex_e:
                logger.warning(f"跳过excludeSwitches选项 (兼容性问题): {ex_e}")
                # 使用替代方法
                options.add_argument('--disable-automation')
                options.add_argument('--disable-extensions')
            
            # 设置代理（如果有）
            if self.current_proxy:
                if self.current_proxy.startswith('http'):
                    options.add_argument(f'--proxy-server={self.current_proxy}')
                else:
                    options.add_argument(f'--proxy-server=socks5://{self.current_proxy}')
            
            # 尝试使用兼容的Chrome驱动初始化
            try:
                self.browser = uc.Chrome(options=options, version_main=None)
            except Exception as chrome_e:
                logger.warning(f"标准Chrome初始化失败，尝试简化配置: {chrome_e}")
                # 简化选项重试
                simple_options = uc.ChromeOptions()
                if self.use_headless_browser:
                    simple_options.add_argument('--headless')
                simple_options.add_argument('--no-sandbox')
                simple_options.add_argument('--disable-dev-shm-usage')
                self.browser = uc.Chrome(options=simple_options)
            
            # 只在浏览器成功初始化后执行脚本
            if self.browser:
                try:
                    self.browser.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                except Exception as script_e:
                    logger.warning(f"执行反检测脚本失败: {script_e}")
            
            logger.info("浏览器初始化成功")
            
        except Exception as e:
            logger.error(f"浏览器初始化失败: {e}")
            self.browser = None
    
    def _handle_manual_captcha(self, url: str) -> Optional[str]:
        """处理需要人工解决的CAPTCHA"""
        logger.info("=" * 60)
        logger.info("🤖 检测到CAPTCHA或429错误，需要人工处理")
        logger.info("=" * 60)
        logger.info(f"请在浏览器中手动完成CAPTCHA验证")
        logger.info(f"页面URL: {url}")
        
        # 强制切换到有头模式
        original_headless = self.use_headless_browser
        self.use_headless_browser = False
        
        try:
            # 关闭现有浏览器（如果有）
            if self.browser:
                try:
                    self.browser.quit()
                except:
                    pass
                self.browser = None
            
            # 重新初始化为有头模式
            self._init_browser()
            
            if not self.browser:
                logger.error("无法初始化浏览器进行手动CAPTCHA处理")
                return None
            
            # 导航到页面
            logger.info("🌐 正在打开浏览器窗口...")
            self.browser.get(url)
            
            # 等待页面加载
            time.sleep(3)
            
            logger.info("🎯 浏览器窗口已打开！")
            logger.info("请在浏览器中：")
            logger.info("1. 完成任何CAPTCHA验证")
            logger.info("2. 等待页面正常加载")
            logger.info("3. 如果遇到403/429错误页面，请刷新页面直到正常")
            logger.info("4. ⚠️  请不要关闭浏览器窗口！")
            logger.info("5. 完成后，请回到终端按回车键继续...")
            logger.info("=" * 60)
            
            input("\n⏳ 请完成浏览器中的验证，然后按回车键继续...")
            
            # 获取当前页面内容
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f"🔄 正在获取页面内容 (尝试 {attempt + 1}/{max_retries})...")
                    
                    # 检查浏览器窗口是否还存在
                    try:
                        window_handles = self.browser.window_handles
                        if not window_handles:
                            logger.warning("⚠️  浏览器窗口已关闭")
                            retry_choice = input("浏览器窗口已关闭，是否重新打开？(y/n): ").lower().strip()
                            if retry_choice == 'y':
                                return self._handle_manual_captcha(url)
                            else:
                                return None
                    except Exception as e:
                        logger.warning(f"⚠️  无法检查浏览器状态: {e}")
                        retry_choice = input("浏览器连接异常，是否重新打开？(y/n): ").lower().strip()
                        if retry_choice == 'y':
                            return self._handle_manual_captcha(url)
                        else:
                            return None
                    
                    # 等待页面完全加载
                    time.sleep(3)
                    
                    # 获取当前URL
                    current_url = self.browser.current_url
                    logger.info(f"📍 当前页面URL: {current_url}")
                    
                    # 检查页面是否还在加载
                    page_state = self.browser.execute_script("return document.readyState")
                    logger.info(f"📄 页面状态: {page_state}")
                    
                    if page_state != "complete":
                        logger.info("⏳ 页面仍在加载，等待...")
                        time.sleep(5)
                    
                    # 获取页面源码
                    page_source = self.browser.page_source
                    
                    # 检查页面源码长度
                    page_length = len(page_source) if page_source else 0
                    logger.info(f"📏 页面内容长度: {page_length} 字符")
                    
                    if not page_source or page_length < 100:
                        logger.warning(f"⚠️  页面内容太短或为空 (长度: {page_length})")
                        if attempt < max_retries - 1:
                            logger.info("🔄 将重新尝试获取...")
                            continue
                        else:
                            retry = input("页面内容异常，是否手动重试？(y/n): ").lower().strip()
                            if retry == 'y':
                                return self._handle_manual_captcha(url)
                            else:
                                return None
                    
                    # 解析页面内容
                    soup = BeautifulSoup(page_source, 'html.parser')
                    page_text = soup.get_text().lower() if soup else ""
                    
                    # 输出页面调试信息
                    page_title = soup.title.string if soup.title else "无标题"
                    logger.info(f"📰 页面标题: {page_title}")
                    
                    # 检查是否包含Scholar内容
                    has_scholar_content = (
                        "scholar" in page_text or 
                        "google scholar" in page_text or
                        "cited by" in page_text or
                        "citations" in page_text or
                        "结果" in page_text or  # 中文版本
                        "results" in page_text
                    )
                    
                    # 检查是否还有CAPTCHA或错误
                    has_captcha = self._is_captcha_page(soup)
                    has_errors = (
                        "sorry" in page_text or 
                        "unusual traffic" in page_text or
                        "too many requests" in page_text or
                        "403" in page_text or
                        "forbidden" in page_text
                    )
                    
                    logger.info(f"🔍 页面检查结果:")
                    logger.info(f"   - 包含Scholar内容: {'是' if has_scholar_content else '否'}")
                    logger.info(f"   - 检测到CAPTCHA: {'是' if has_captcha else '否'}")
                    logger.info(f"   - 检测到错误: {'是' if has_errors else '否'}")
                    
                    if not has_captcha and not has_errors:
                        if has_scholar_content:
                            logger.info("✅ 验证成功！页面已正常加载，包含Scholar内容")
                            return page_source
                        else:
                            # 即使没有明确的Scholar标识，也可能是正常页面
                            logger.warning("⚠️  未明确检测到Scholar内容，但页面似乎正常")
                            logger.info("💡 提示：这可能是因为页面内容格式变化或语言设置")
                            use_anyway = input("是否仍要使用此页面内容？(y/n): ").lower().strip()
                            if use_anyway == 'y':
                                logger.info("✅ 用户确认使用页面内容")
                                return page_source
                            else:
                                retry = input("是否重新尝试验证？(y/n): ").lower().strip()
                                if retry == 'y':
                                    return self._handle_manual_captcha(url)
                                else:
                                    return None
                    else:
                        logger.warning("⚠️  页面似乎仍有问题")
                        if has_captcha:
                            logger.info("🔍 检测到CAPTCHA，请确保已完成验证")
                        if has_errors:
                            logger.info("🔍 检测到错误页面，请刷新页面或等待")
                        
                        retry = input("是否重试？(y/n): ").lower().strip()
                        if retry == 'y':
                            return self._handle_manual_captcha(url)
                        else:
                            return None
                    
                except Exception as e:
                    logger.error(f"获取页面内容时出错: {e}")
                    if attempt < max_retries - 1:
                        logger.info("🔄 将重新尝试...")
                        time.sleep(2)
                        continue
                    else:
                        retry = input("获取页面内容失败，是否重新尝试？(y/n): ").lower().strip()
                        if retry == 'y':
                            return self._handle_manual_captcha(url)
                        else:
                            return None
            
            logger.error("无法获取有效的页面内容")
            return None
            
        finally:
            # 恢复原始的无头模式设置
            self.use_headless_browser = original_headless
    
    def _handle_captcha_or_block(self, url: str, response_text: str, attempt: int):
        """处理CAPTCHA或封禁的通用方法"""
        logger.warning(f"遇到CAPTCHA或封禁 (尝试 {attempt + 1})")
        
        # 轮换代理（如果有）
        if self.proxy_list:
            self._rotate_proxy()
            logger.info("已轮换代理")
        
        # 更新请求头
        self._update_headers()
        logger.info("已更新请求头")
        
        # 渐进式延迟
        delay = 5 + attempt * 3 + random.uniform(1, 5)
        logger.info(f"等待 {delay:.1f} 秒后重试...")
        time.sleep(delay)
    
    def _adaptive_delay(self):
        """自适应延迟策略"""
        self.request_count += 1
        
        # 基础延迟
        base_delay = random.uniform(*self.delay_range)
        
        # 根据请求频率调整延迟
        if self.request_count % 10 == 0:
            base_delay *= 1.5  # 每10个请求增加50%延迟
        
        # 如果最近遇到过429错误，增加延迟
        if self.last_429_time:
            time_since_429 = datetime.now() - self.last_429_time
            if time_since_429 < timedelta(minutes=5):
                base_delay *= 2
        
        time.sleep(base_delay)
    
    def _handle_429_error(self, url: str) -> Optional[str]:
        """处理429错误 - Too Many Requests"""
        current_time = datetime.now()
        self.last_429_time = current_time
        self.consecutive_429_count += 1
        
        logger.warning(f"遇到429错误 (连续第{self.consecutive_429_count}次): {url}")
        
        if self.skip_429_errors:
            logger.info("⏭️  启用了跳过429错误模式，执行快速策略")
            
            # 快速策略：短暂延迟后继续
            retry_delay = 2 + random.uniform(1, 3)
            logger.info(f"   ✓ 执行快速延迟: {retry_delay:.1f} 秒")
            time.sleep(retry_delay)
            
            # 更新请求头
            self._update_headers()
            logger.info("   ✓ 已更新请求头")
            
            logger.info("   ✓ 快速策略完成，继续尝试")
            return None  # 返回None，让调用方继续尝试
        
        # 默认模式：完整的429处理策略
        logger.info("🔄 执行完整的429错误处理策略...")
        
        # 1. 轮换代理
        if self.proxy_list:
            self._rotate_proxy()
            logger.info("   ✓ 已轮换代理")
        
        # 2. 更新请求头
        self._update_headers()
        logger.info("   ✓ 已更新请求头")
        
        # 3. 计算延迟时间
        base_delay = 10  # 基础延迟10秒
        progressive_delay = self.consecutive_429_count * 5  # 渐进式延迟
        random_delay = random.uniform(5, 15)  # 随机延迟
        total_delay = base_delay + progressive_delay + random_delay
        
        logger.info(f"   ✓ 执行延迟策略: {total_delay:.1f} 秒")
        logger.info(f"     - 基础延迟: {base_delay}s")
        logger.info(f"     - 渐进延迟: {progressive_delay}s (连续{self.consecutive_429_count}次)")
        logger.info(f"     - 随机延迟: {random_delay:.1f}s")
        
        time.sleep(total_delay)
        
        # 4. 如果连续429错误太多，启用手动验证
        if self.consecutive_429_count >= 3 and self.use_browser_fallback:
            logger.warning("连续429错误过多，启用手动验证模式")
            return self._handle_manual_captcha(url)
        
        logger.info("   ✓ 429错误处理完成，继续尝试")
        return None
    
    def _reset_429_tracking(self):
        """重置429错误跟踪"""
        if self.consecutive_429_count > 0:
            logger.info(f"✅ 成功请求，重置429错误计数 (之前连续{self.consecutive_429_count}次)")
        self.consecutive_429_count = 0
        self.last_429_time = None
    
    def close(self):
        """清理资源"""
        if self.browser:
            try:
                self.browser.quit()
                logger.info("浏览器已关闭")
            except Exception as e:
                logger.error(f"关闭浏览器时出错: {e}")
        
        if self.session:
            self.session.close()
            logger.info("会话已关闭")

def print_citation_tree(node: CitationNode, indent: int = 0, max_title_length: int = 80):
    """打印引用树的美化版本"""
    if not node:
        return
    
    prefix = "  " * indent
    
    # 截断过长的标题
    title = node.paper.title
    if len(title) > max_title_length:
        title = title[:max_title_length-3] + "..."
    
    # 格式化输出
    citation_info = f"(引用数: {node.paper.citation_count})" if node.paper.citation_count > 0 else ""
    year_info = f"({node.paper.year})" if node.paper.year else ""
    
    print(f"{prefix}├─ {title}")
    if node.paper.authors:
        print(f"{prefix}   作者: {node.paper.authors}")
    if year_info or citation_info:
        info_line = " ".join(filter(None, [year_info, citation_info]))
        print(f"{prefix}   {info_line}")
    if node.paper.url:
        print(f"{prefix}   链接: {node.paper.url}")
    print()
    
    # 递归打印子节点
    for child in node.children:
        print_citation_tree(child, indent + 1, max_title_length)

def save_tree_to_json(node: CitationNode, filename: str):
    """将引用树保存为JSON格式"""
    def node_to_dict(n: CitationNode) -> dict:
        return {
            'paper': {
                'title': n.paper.title,
                'authors': n.paper.authors,
                'year': n.paper.year,
                'citation_count': n.paper.citation_count,
                'url': n.paper.url,
                'cited_by_url': n.paper.cited_by_url,
                'abstract': n.paper.abstract
            },
            'depth': n.depth,
            'children': [node_to_dict(child) for child in n.children]
        }
    
    tree_dict = node_to_dict(node)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(tree_dict, f, ensure_ascii=False, indent=2)
    
    logger.info(f"引用树已保存到: {filename}")

def load_tree_from_json(filename: str) -> CitationNode:
    """从JSON文件加载引用树"""
    def dict_to_node(data: dict) -> CitationNode:
        paper = Paper(**data['paper'])
        node = CitationNode(paper=paper, children=[], depth=data['depth'])
        node.children = [dict_to_node(child) for child in data['children']]
        return node
    
    with open(filename, 'r', encoding='utf-8') as f:
        tree_dict = json.load(f)
    
    return dict_to_node(tree_dict)

# 使用示例
if __name__ == "__main__":
    # 示例使用
    crawler = GoogleScholarCrawler(
        max_depth=2,
        max_papers_per_level=5,
        delay_range=(2, 4),
        skip_429_errors=True  # 启用跳过429错误模式
    )
    
    # 从引用页面开始爬取
    start_url = "https://scholar.google.com/scholar?cites=1234567890&as_sdt=2005&sciodt=0,5&hl=en"
    
    try:
        tree = crawler.build_citation_tree(start_url)
        if tree:
            print_citation_tree(tree)
            save_tree_to_json(tree, "citation_tree.json")
        else:
            print("未能构建引用树")
    finally:
        crawler.close()
