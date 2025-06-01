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

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    
    def __init__(self, max_depth=3, max_papers_per_level=10, delay_range=(2, 5)):
        self.max_depth = max_depth
        self.max_papers_per_level = max_papers_per_level
        self.delay_range = delay_range
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
        
        self.visited_urls.add(cited_by_url)
        
        try:
            logger.info(f"正在爬取: {cited_by_url}")
            
            # 使用自适应延迟
            self._adaptive_delay()
            
            # 每隔几个请求更新一次请求头
            if self.request_count % 5 == 0:
                self._update_headers()
            
            response = self.session.get(cited_by_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 检测CAPTCHA或封禁
            if self._is_captcha_page(soup):
                self._handle_captcha_or_block(cited_by_url, response.text)
                return []
            
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
            
            logger.info(f"找到 {len(papers)} 篇有效引用论文")
            
            # 如果没有找到任何有效论文，记录调试信息
            if not papers and paper_divs:
                debug_file = f"debug_no_papers_{int(time.time())}.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                logger.warning(f"解析失败，已保存调试页面到: {debug_file}")
            
            return papers
            
        except requests.RequestException as e:
            logger.error(f"网络请求失败: {e}")
            return []
        except Exception as e:
            logger.error(f"解析页面失败: {e}")
            return []
    
    def _get_paper_from_scholar_url(self, scholar_url: str) -> Optional[Paper]:
        """从Scholar搜索URL获取原始论文信息"""
        try:
            logger.info(f"获取原始论文信息: {scholar_url}")
            
            self._adaptive_delay()
            
            response = self.session.get(scholar_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 检测CAPTCHA或封禁
            if self._is_captcha_page(soup):
                self._handle_captcha_or_block(scholar_url, response.text)
                return None
            
            # 查找第一个搜索结果
            first_result = soup.find('div', class_='gs_r')
            if not first_result:
                # 尝试其他可能的选择器
                first_result = soup.find('div', class_='gs_ri') or soup.find('div', {'data-lid': True})
            
            if first_result:
                return self._parse_paper_info(first_result)
            else:
                logger.warning("未找到搜索结果")
                
        except Exception as e:
            logger.error(f"获取原始论文信息失败: {e}")
        
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
            
        return False
    
    def _handle_captcha_or_block(self, url: str, response_text: str) -> bool:
        """处理CAPTCHA或封禁情况"""
        logger.warning(f"检测到CAPTCHA或访问被阻止: {url}")
        
        # 保存调试信息
        debug_file = f"debug_captcha_{int(time.time())}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(response_text)
        logger.info(f"已保存调试页面到: {debug_file}")
        
        # 增加延迟时间
        delay = random.uniform(10, 20)
        logger.info(f"遇到CAPTCHA，等待 {delay:.1f} 秒...")
        time.sleep(delay)
        
        # 更新请求头
        self._update_headers()
        
        return False
    
    def _adaptive_delay(self):
        """自适应延迟策略"""
        self.request_count += 1
        
        # 基础延迟
        base_delay = random.uniform(*self.delay_range)
        
        # 根据请求次数增加延迟
        if self.request_count > 10:
            base_delay *= 1.5
        if self.request_count > 20:
            base_delay *= 2
        
        # 偶尔使用更长的延迟
        if random.random() < 0.1:  # 10%概率使用长延迟
            base_delay *= 2
        
        logger.debug(f"延迟 {base_delay:.1f} 秒 (请求次数: {self.request_count})")
        time.sleep(base_delay)

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
        max_depth=3,  # 最大递归深度
        max_papers_per_level=5,  # 每层最多爬取的论文数
        delay_range=(1, 3)  # 请求间隔时间范围（秒）
    )
    
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
        
    else:
        print("❌ 无法构建引用树")

if __name__ == "__main__":
    main()
