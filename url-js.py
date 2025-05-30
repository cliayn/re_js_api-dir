import os
import re
import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
import hashlib

# ================== 通用工具函数 ==================
def get_valid_filename(url):
    """从URL生成有效的文件名"""
    parsed = urlparse(url)
    name = parsed.path.split("/")[-1] or "index"
    if not name.endswith('.js'):
        name += '.js'
    name = ''.join(c for c in name if c.isalnum() or c in ['-', '_', '.'])
    return name

def save_js_file(url, directory, session, referer):
    """下载并保存JS文件"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/javascript, application/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': referer
        }
        
        response = session.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            filename = get_valid_filename(url)
            filepath = os.path.join(directory, filename)
            
            # 处理重复文件名
            counter = 1
            while os.path.exists(filepath):
                name, ext = os.path.splitext(filename)
                filepath = os.path.join(directory, f"{name}_{counter}{ext}")
                counter += 1
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"✅ 保存成功: {os.path.basename(filepath)}")
            return filepath
        else:
            print(f"❌ 响应状态码 {response.status_code}: {url}")
    except Exception as e:
        print(f"❌ 下载失败 {url}: {str(e)}")
    return None

def extract_js_links(url, session):
    """从URL中提取所有JS链接"""
    try:
        print(f"🌐 正在解析页面: {url}")
        response = session.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        js_links = []
        
        for tag in soup.find_all(['script', 'link']):
            src = None
            if tag.name == 'script' and tag.get('src'):
                src = tag['src']
            elif tag.name == 'link' and tag.get('rel') == ['stylesheet'] and tag.get('href'):
                if tag['href'].endswith('.js'):
                    src = tag['href']
            
            if src:
                full_url = urljoin(url, src)
                if full_url.endswith('.js') or 'javascript' in tag.get('type', '').lower():
                    js_links.append(full_url)
        
        print(f"🔍 找到 {len(js_links)} 个JS文件链接")
        return js_links
    except Exception as e:
        print(f"⚠️ 解析失败 {url}: {str(e)}")
        return []

def get_path_hash(paths):
    """计算路径集合的哈希值用于比较"""
    sorted_paths = sorted(paths)
    path_str = ''.join(sorted_paths)
    return hashlib.md5(path_str.encode('utf-8')).hexdigest()

# ================== 第一部分：下载原始JS文件 ==================
def download_initial_js_files(base_url, api_js_directory):
    """下载目标页面所有JS文件"""
    os.makedirs(api_js_directory, exist_ok=True)
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    })
    
    downloaded_files = []
    
    try:
        # 获取主页面JS链接
        js_links = extract_js_links(base_url, session)
        
        # 下载JS文件
        success_count = 0
        for i, js_url in enumerate(set(js_links), 1):
            print(f"📥 正在下载 ({i}/{len(js_links)}): {js_url}")
            saved_path = save_js_file(js_url, api_js_directory, session, base_url)
            if saved_path:
                success_count += 1
                downloaded_files.append(saved_path)
        
        print(f"\n🎉 原始JS文件下载完成! 成功保存 {success_count}/{len(js_links)} 个文件")
        return downloaded_files, session

    except Exception as e:
        print(f"⚠️ 发生错误: {str(e)}")
        return downloaded_files, None

# ================== 第二部分：分析JS文件提取API路径 ==================
def analyze_js_files_for_paths(api_js_directory):
    """分析JS文件并提取API路径"""
    pattern_groups = {
        "PagePath Matches": [
            (re.compile(r'pagePath:\s*"(.*?)"'), "pagePath_double_quotes"),
            (re.compile(r"pagePath:\s*'(.*?)'"), "pagePath_single_quotes"),
        ],
        "Path Matches": [
            (re.compile(r'path:\s*"(.*?)"'), "path_double_quotes"),
            (re.compile(r"path:\s*'(.*?)'"), "path_single_quotes"),
            (re.compile(r'url:\s*"([^"]+)"'), "url_double_quotes"),
            (re.compile(r"url:\s*'([^']+)'"), "url_single_quotes"),
        ]
    }

    # 收集所有路径
    all_paths = set()
    
    # 遍历JS文件
    total_files = 0
    processed_files = 0
    for root, _, files in os.walk(api_js_directory):
        for file in files:
            if file.endswith(".js"):
                total_files += 1
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        processed_files += 1
                        
                        # 对每个分组和正则表达式进行匹配
                        for group, patterns in pattern_groups.items():
                            for pattern, _ in patterns:
                                matches = pattern.findall(content)
                                for match in matches:
                                    # 标准化路径：确保以/开头，去掉结尾的/
                                    path = match.strip()
                                    if not path.startswith('/'):
                                        path = '/' + path
                                    if path.endswith('/'):
                                        path = path[:-1]
                                    all_paths.add(path)
                except Exception as e:
                    print(f"⚠️ 无法读取文件 {file_path}: {e}")

    print(f"\n🔍 路径分析完成! 共处理 {processed_files}/{total_files} 个JS文件")
    print(f"📊 发现 {len(all_paths)} 个唯一路径")
    
    return sorted(all_paths)

# ================== 第三部分：构造并请求新URL ==================
def construct_and_request_urls(base_url, paths, session, api_js_directory):
    """构造两种URL格式并请求新JS文件"""
    # 解析基础URL
    parsed_base = urlparse(base_url)
    base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
    
    # 构造两种URL
    direct_urls = []
    hash_urls = []
    
    for path in paths:
        # 直接连接格式: https://domain.com/path
        direct_url = urljoin(base_domain, path)
        direct_urls.append(direct_url)
        
        # #连接格式: https://domain.com/#/path
        hash_path = f"/#{path}" if not path.startswith("#") else path
        hash_url = urlunparse((
            parsed_base.scheme,
            parsed_base.netloc,
            parsed_base.path,
            parsed_base.params,
            parsed_base.query,
            hash_path
        ))
        hash_urls.append(hash_url)
    
    print(f"\n🔗 构造了 {len(direct_urls)} 个直接连接URL")
    print(f"🔗 构造了 {len(hash_urls)} 个#连接URL")
    
    # 用于存储所有新发现的JS链接
    all_new_js_links = set()
    
    # 请求所有直接连接URL
    print("\n🌐 开始请求直接连接URL...")
    for i, url in enumerate(direct_urls, 1):
        print(f"🔍 正在处理直接连接 ({i}/{len(direct_urls)}): {url}")
        try:
            js_links = extract_js_links(url, session)
            all_new_js_links.update(js_links)
            # 避免请求过快
            time.sleep(0.5)
        except Exception as e:
            print(f"⚠️ 请求失败 {url}: {str(e)}")
    
    # 请求所有#连接URL
    print("\n🌐 开始请求#连接URL...")
    for i, url in enumerate(hash_urls, 1):
        print(f"🔍 正在处理#连接 ({i}/{len(hash_urls)}): {url}")
        try:
            js_links = extract_js_links(url, session)
            all_new_js_links.update(js_links)
            time.sleep(0.5)
        except Exception as e:
            print(f"⚠️ 请求失败 {url}: {str(e)}")
    
    print(f"\n🔍 总共发现 {len(all_new_js_links)} 个新的JS文件链接")
    
    # 下载新发现的JS文件
    success_count = 0
    new_files = []
    for i, js_url in enumerate(all_new_js_links, 1):
        print(f"📥 正在下载新JS文件 ({i}/{len(all_new_js_links)}): {js_url}")
        saved_path = save_js_file(js_url, api_js_directory, session, base_url)
        if saved_path:
            success_count += 1
            new_files.append(saved_path)
    
    print(f"\n🎉 新JS文件下载完成! 成功保存 {success_count}/{len(all_new_js_links)} 个文件")
    return new_files

# ================== 第四部分：最终路径分析输出 ==================
def final_path_analysis(api_js_directory, output_file):
    """对所有JS文件进行最终路径分析"""
    # 定义匹配的正则表达式和分类标签
    pattern_groups = {
        "PagePath Matches": [
            (re.compile(r'pagePath:\s*"(.*?)"'), "pagePath_double_quotes"),
            (re.compile(r"pagePath:\s*'(.*?)'"), "pagePath_single_quotes"),
        ],
        "Path Matches": [
            (re.compile(r'path:\s*"(.*?)"'), "path_double_quotes"),
            (re.compile(r"path:\s*'(.*?)'"), "path_single_quotes"),
            (re.compile(r'url:\s*"([^"]+)"'), "url_double_quotes"),
            (re.compile(r'url: "([^"]+)'), "url_double_quotes"),
        ],
        "GET Matches": [
            (re.compile(r'get\([^()]*?"([^"]*?)"[^()]*?\)'), "get_double_quotes"),
            (re.compile(r"get\([^()]*?['\"]([^'\"]*?)['\"][^()]*?\)"), "get_single_quotes"),
        ],
        "POST Matches": [
            (re.compile(r'post\([^()]*?"([^"]*?)"[^()]*?\)'), "post_double_quotes"),
            (re.compile(r"POST\([^()]*?['\"]([^'\"]*?)['\"][^()]*?\)"), "post_single_quotes"),
        ]
    }

    # 初始化结果存储
    matched_results = {group: [] for group in pattern_groups}
    total_files = 0
    processed_files = 0

    # 遍历目录下的所有 .js 文件
    for root, _, files in os.walk(api_js_directory):
        for file in files:
            if file.endswith(".js"):
                total_files += 1
                file_path = os.path.join(root, file)
                try:
                    # 打开文件并读取内容
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        processed_files += 1
                        
                        # 对每个分组和正则表达式进行匹配
                        for group, patterns in pattern_groups.items():
                            for pattern, label in patterns:
                                matches = pattern.findall(content)
                                if matches:
                                    for match in matches:
                                        # 按分组保存匹配的路径和标签
                                        matched_results[group].append((match.strip(), label))
                except Exception as e:
                    print(f"⚠️ 无法读取文件 {file_path}: {e}")

    print(f"\n🔍 最终路径分析完成! 共处理 {processed_files}/{total_files} 个JS文件")
    
    # 将结果写入文件
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            total_paths = 0
            
            for group, results in matched_results.items():
                if results:
                    f.write(f"===== {group} =====\n")
                    # 去重、排序
                    unique_results = sorted(set(results), key=lambda x: x[0])
                    max_length = max(len(path) for path, _ in unique_results) if unique_results else 0
                    
                    for path, label in unique_results:
                        f.write(f"{path.ljust(max_length + 2)}\t[{label}]\n")
                        total_paths += 1
                    f.write("\n")  # 分块之间加空行
            
            f.write(f"===== 统计信息 =====\n")
            f.write(f"总提取路径数: {total_paths}\n")
            f.write(f"分析文件数: {processed_files}\n")
            f.write(f"文件来源目录: {api_js_directory}\n")
            f.write(f"分析时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
        print(f"📝 匹配的路径已按分类写入 {output_file}")
        print(f"📊 共提取 {total_paths} 个API路径")
        return total_paths
    except Exception as e:
        print(f"⚠️ 无法写入文件 {output_file}: {e}")
        return 0

# ================== 主程序 ==================
if __name__ == "__main__":
    # 配置
    api_js_directory = r"D:\Desktop\杂项\缴费"
    output_file = os.path.join(api_js_directory, "path.txt")
    
    # 用户输入URL
    target_url = input("请输入目标URL: ").strip()
    
    # 第一步：下载原始JS文件
    print("\n" + "="*60)
    print("第一步：下载原始JS文件")
    print("="*60)
    initial_files, session = download_initial_js_files(target_url, api_js_directory)
    
    if session is None:
        print("\n❌ 初始下载失败，程序终止")
        exit(1)
    
    # 第二步：初始路径分析
    print("\n\n" + "="*60)
    print("第二步：初始路径分析")
    print("="*60)
    paths = analyze_js_files_for_paths(api_js_directory)
    
    # 循环控制变量
    max_iterations = 5  # 最大循环次数
    iteration = 1
    previous_paths = set()
    current_paths = set(paths)
    all_new_files = []
    
    # 路径发现循环
    while iteration <= max_iterations and previous_paths != current_paths:
        print(f"\n\n" + "="*60)
        print(f"路径发现循环 #{iteration}/{max_iterations}")
        print("="*60)
        
        # 保存当前路径用于下次比较
        previous_paths = current_paths
        
        if paths:
            # 显示前5个路径作为示例
            print("\n📋 部分提取路径示例:")
            for i, path in enumerate(paths[:5], 1):
                print(f"{i}. {path}")
            if len(paths) > 5:
                print(f"... 以及另外 {len(paths)-5} 个路径")
            
            # 第三步：构造URL并请求新JS文件
            print("\n" + "-"*50)
            print("构造URL并请求新JS文件")
            print("-"*50)
            new_files = construct_and_request_urls(target_url, paths, session, api_js_directory)
            all_new_files.extend(new_files)
            
            # 第四步：再次分析路径
            print("\n" + "-"*50)
            print("再次分析JS文件提取路径")
            print("-"*50)
            new_paths = analyze_js_files_for_paths(api_js_directory)
            current_paths = set(new_paths)
            
            # 计算新增路径数
            new_path_count = len(current_paths - previous_paths)
            print(f"📈 新增路径数: {new_path_count}")
            
            # 准备下一次迭代
            paths = new_paths
            iteration += 1
        else:
            print("\n⚠️ 未提取到任何路径，终止循环")
            break
    
    # 最终路径分析
    print("\n\n" + "="*60)
    print("最终路径分析输出")
    print("="*60)
    final_path_analysis(api_js_directory, output_file)
    
    # 最终报告
    print("\n\n" + "="*60)
    print("✅ 任务完成!")
    print("="*60)
    print(f"📁 保存目录: {api_js_directory}")
    print(f"📄 初始下载JS文件: {len(initial_files)} 个")
    print(f"📄 新发现JS文件: {len(all_new_files)} 个")
    print(f"🔄 循环次数: {iteration-1}/{max_iterations}")
    print(f"📊 最终路径数: {len(current_paths)}")
    print(f"📝 最终分析结果: {output_file}")