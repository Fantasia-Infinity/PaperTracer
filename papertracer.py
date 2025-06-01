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
                 use_browser_fallback=True, captcha_service_api_key=None, proxy_list=None):
        self.max_depth = max_depth
        self.max_papers_per_level = max_papers_per_level
        self.delay_range = delay_range
        self.max_captcha_retries = max_captcha_retries
        self.use_browser_fallback = use_browser_fallback and BROWSER_AVAILABLE
        self.use_headless_browser = True  # 添加缺失的属性
        self.captcha_service_api_key = captcha_service_api_key
        self.proxy_list = proxy_list or []
        self.proxy_index = 0
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
                    
                    # 如果还没尝试过浏览器方法，且配置允许，则尝试浏览器方法
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
                
                logger.info(f"找到 {len(papers)} 篇有效引用论文 from {cited_by_url}")
                
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
                    self._handle_429_error()
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
                    
                    # 如果还没尝试过浏览器方法，且配置允许，则尝试浏览器方法
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
                    self._handle_429_error()
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
        
        # 获取引用这篇论文的文章
        citing_papers = self._fetch_citations(root_paper.cited_by_url)
        
        # 为每个引用论文递归构建子树
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
        
        # 获取引用这篇论文的文章
        citing_papers = self._fetch_citations(paper.cited_by_url)
        
        # 为每个引用论文递归构建子树
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
    
    def _handle_captcha_or_block(self, url: str, response_text: str, attempt: int) -> bool:
        """处理CAPTCHA或封禁情况"""
        logger.warning(f"检测到CAPTCHA或访问被阻止: {url} (尝试 #{attempt+1})")
        
        # 保存调试信息
        debug_file = f"debug_captcha_{int(time.time())}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(response_text)
        logger.info(f"已保存调试页面到: {debug_file}")
        
        # 轮换代理
        self._rotate_proxy()
        
        # 指数退避延迟
        delay = random.uniform(10, 20) * (1.5 ** attempt)
        logger.info(f"遇到CAPTCHA，等待 {delay:.1f} 秒 (指数退避)...")
        time.sleep(delay)
        
        # 更新请求头
        self._update_headers()
        
        return False
    
    def _adaptive_delay(self):
        """自适应延迟策略 - 增强版，更好地应对Google Scholar反爬虫"""
        self.request_count += 1
        
        # 检查是否最近遇到了429错误
        delay_multiplier = 1.0
        if self.last_429_time:
            time_since_429 = datetime.now() - self.last_429_time
            if time_since_429.total_seconds() < 300:  # 5分钟内
                delay_multiplier = 2.0 + self.consecutive_429_count * 0.5
                logger.info(f"最近遇到429错误，增加延迟倍数: {delay_multiplier:.1f}")
        
        # 基础延迟
        base_delay = random.uniform(*self.delay_range) * delay_multiplier
        
        # 根据请求次数动态增加延迟 - 更激进的策略
        if self.request_count > 5:
            base_delay *= 1.3
        if self.request_count > 10:
            base_delay *= 1.8
        if self.request_count > 20:
            base_delay *= 2.5
        if self.request_count > 30:
            base_delay *= 3.0
        
        # 增加随机性以避免检测模式
        if random.random() < 0.2:  # 20%概率使用更长延迟
            base_delay *= random.uniform(2, 4)
        
        # 每隔一段时间使用特别长的延迟
        if self.request_count % 15 == 0:
            base_delay *= random.uniform(3, 6)
            logger.info(f"使用特别长的延迟以降低被检测概率: {base_delay:.1f} 秒")
        
        # 限制最大延迟时间，避免过度等待
        base_delay = min(base_delay, 300)  # 最多5分钟
        
        logger.debug(f"延迟 {base_delay:.1f} 秒 (请求次数: {self.request_count})")
        time.sleep(base_delay)

    def _handle_429_error(self):
        """专门处理429错误的方法"""
        self.last_429_time = datetime.now()
        self.consecutive_429_count += 1
        
        # 指数退避，但有上限
        backoff_delay = min(30 * (2 ** min(self.consecutive_429_count, 5)), 600)  # 最多10分钟
        logger.warning(f"遇到429错误 (连续第{self.consecutive_429_count}次)，等待 {backoff_delay} 秒...")
        
        # 更新User-Agent
        self._update_headers()
        
        time.sleep(backoff_delay)

    def _reset_429_tracking(self):
        """重置429错误跟踪"""
        if self.consecutive_429_count > 0:
            logger.info(f"成功请求，重置429错误计数 (之前连续{self.consecutive_429_count}次)")
            self.consecutive_429_count = 0
            
    def save_session_state(self, filepath: str):
        """保存会话状态到文件"""
        state = {
            'session_id': self.session_id,
            'visited_urls': list(self.visited_urls),
            'request_count': self.request_count,
            'last_429_time': self.last_429_time,
            'consecutive_429_count': self.consecutive_429_count,
            'current_proxy_index': self.proxy_index if hasattr(self, 'proxy_index') else 0
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, default=str)
            logger.info(f"会话状态已保存到: {filepath}")
        except Exception as e:
            logger.error(f"保存会话状态失败: {e}")

    def load_session_state(self, filepath: str) -> bool:
        """从文件加载会话状态"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            self.session_id = state.get('session_id', self.session_id)
            self.visited_urls = set(state.get('visited_urls', []))
            self.request_count = state.get('request_count', 0)
            self.consecutive_429_count = state.get('consecutive_429_count', 0)
            self.proxy_index = state.get('current_proxy_index', 0)
            
            # 处理时间字符串
            last_429_str = state.get('last_429_time')
            if last_429_str and last_429_str != 'None':
                try:
                    self.last_429_time = datetime.fromisoformat(last_429_str.replace('Z', '+00:00'))
                except:
                    self.last_429_time = None
            
            logger.info(f"会话状态已从 {filepath} 恢复")
            logger.info(f"  - 会话ID: {self.session_id}")
            logger.info(f"  - 已访问URL数: {len(self.visited_urls)}")
            logger.info(f"  - 请求计数: {self.request_count}")
            logger.info(f"  - 连续429错误: {self.consecutive_429_count}")
            return True
            
        except Exception as e:
            logger.error(f"加载会话状态失败: {e}")
            return False
def print_citation_tree(node: CitationNode, indent: str = ""):
    """打印引用树"""
    print(f"{indent}📄 {node.paper.title}")
    print(f"{indent}   👥 {node.paper.authors}")
    if node.paper.year:
        print(f"{indent}   📅 {node.paper.year}")
    if node.paper.citation_count > 0:
        print(f"{indent}   📊 被引用 {node.paper.citation_count} 次")
    print()
    
    for child in node.children:
        print_citation_tree(child, indent + "  ")

def save_tree_to_json(node: CitationNode, filename: str):
    """将引用树保存为JSON文件"""
    def node_to_dict(n: CitationNode) -> dict:
        return {
            "paper": {
                "title": n.paper.title,
                "authors": n.paper.authors,
                "year": n.paper.year,
                "citation_count": n.paper.citation_count,
                "url": n.paper.url,
                "cited_by_url": n.paper.cited_by_url,
                "abstract": n.paper.abstract
            },
            "depth": n.depth,
            "children": [node_to_dict(child) for child in n.children]
        }
    
    tree_dict = node_to_dict(node)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(tree_dict, f, ensure_ascii=False, indent=2)
    
    logger.info(f"引用树已保存到: {filename}")

# 示例使用
sample_link = "https://scholar.google.com/scholar?cites=11002616430871081935&as_sdt=2005&sciodt=0,5&hl=en"

def main():
    """主函数"""
    crawler = GoogleScholarCrawler(
        max_depth=10,  # 最大递归深度
        max_papers_per_level=30,  # 每层最多爬取的论文数
        delay_range=(1, 3)  # 请求间隔时间范围（秒）
    )
    
    # 尝试加载先前的会话
    session_file = "crawler_session.pkl"
    try:
        crawler.load_session(session_file)
    except Exception as e:
        logger.error(f"加载会话时出错，继续执行: {e}")
    
    print("🚀 开始构建引用树...")
    print(f"📋 起始链接: {sample_link}")
    print(f"📊 最大深度: {crawler.max_depth}")
    print(f"📈 每层最多论文数: {crawler.max_papers_per_level}")
    print("-" * 50)
    
    # 构建引用树
    citation_tree = crawler.build_citation_tree(sample_link)
    
    if citation_tree:
        print("\n✅ 引用树构建完成!")
        print("=" * 50)
        print_citation_tree(citation_tree)
        
        # 保存为JSON文件
        save_tree_to_json(citation_tree, "citation_tree.json")
        
        # 统计信息
        def count_nodes(node):
            count = 1
            for child in node.children:
                count += count_nodes(child)
            return count
        
        total_papers = count_nodes(citation_tree)
        print(f"\n📊 统计信息:")
        print(f"   总论文数: {total_papers}")
        print(f"   树的深度: {citation_tree.depth}")
        print(f"   根节点子节点数: {len(citation_tree.children)}")
        
        # 保存当前会话
        crawler.save_session(session_file)
        
    else:
        print("❌ 无法构建引用树")

if __name__ == "__main__":
    main()
