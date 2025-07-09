import os
import regex

# 定义匹配的正则表达式和分类标签
pattern_groups = {
    "PagePath Matches": [
        # 匹配 pagePath: 后面的字符串，支持转义引号
        (regex.compile(r"(?i)pagePath:\s*['\"]((?:[^'\"\\]|\\.)*)['\"]", regex.DOTALL), "pagePath", 1)
    ],
    "Path Matches": [
        # 匹配 path: 后面的字符串，支持转义引号
        (regex.compile(r"(?i)path:\s*['\"]((?:[^'\"\\]|\\.)*)['\"]", regex.DOTALL), "path", 1),
        # 匹配 url: 后面的字符串，支持转义引号
        (regex.compile(r"(?i)url:\s*['\"]((?:[^'\"\\]|\\.)*)['\"]", regex.DOTALL), "url", 1),
        # 匹配 name: 后面的字符串，支持转义引号
        (regex.compile(r"(?i)name:\s*['\"]((?:[^'\"\\]|\\.)*)['\"]", regex.DOTALL), "name", 1),
    ],
    "GET Matches": [
        # 递归匹配 get(...) 中的第一个字符串参数，支持嵌套括号
        (regex.compile(r'(?i)(get)\(((?:[^()]|(?R))++)\)', regex.DOTALL), "", 2),
        # 匹配 url: "...", method: "get" 模式
        (regex.compile(r"(?i)url:\s*['\"]((?:[^'\"\\]|\\.)*)['\"]\s*,\s*method:\s*['\"]get['\"]", regex.DOTALL), "", 1),
    ],
    "POST Matches": [
        # 递归匹配 post(...) 中的第一个字符串参数，支持嵌套括号
        (regex.compile(r'(?i)(post)\(((?:[^()]|(?R))++)\)', regex.DOTALL), "", 2),
        # 匹配 url: "...", method: "post" 模式
        (regex.compile(r"(?i)url:\s*['\"]((?:[^'\"\\]|\\.)*)['\"]\s*,\s*method:\s*['\"]post['\"]", regex.DOTALL), "", 1),
    ],
    "Object": [
        # 匹配对象模式如 key: [{ key: "" 
        (regex.compile(r'\b[a-zA-Z][a-zA-Z0-9]*\b:\[\{\s*\b[a-zA-Z][a-zA-Z0-9]*\b:""', regex.DOTALL), "", 0)
    ]
}

# 定义要遍历的目录
api_js_directory = "js"
output_file = "path.txt"

# 初始化结果存储
matched_results = {group: [] for group in pattern_groups}

# 处理GET/POST参数的辅助函数
def extract_first_string(input_str):
    """从字符串中提取第一个引号包围的字符串（支持转义引号）"""
    # 匹配单引号或双引号包围的字符串
    str_match = regex.search(r'''['"]([^'"]*?(?:\\.[^'"]*?)*?)['"]''', input_str)
    if str_match:
        return str_match.group(1)
    return None

# 遍历目录下的所有 .js 文件
for root, _, files in os.walk(api_js_directory):
    for file in files:
        if file.endswith(".js"):
            file_path = os.path.join(root, file)
            try:
                # 打开文件并读取内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 对每个分组和正则表达式进行匹配
                    for group, patterns in pattern_groups.items():
                        for pattern, label, group_idx in patterns:
                            # 使用finditer处理所有匹配项
                            for match in pattern.finditer(content):
                                try:
                                    if group_idx > 0:  # 需要提取捕获组
                                        raw_value = match.group(group_idx)
                                    else:  # 不需要提取捕获组（Object模式）
                                        raw_value = match.group(0)
                                    
                                    # 特殊处理GET/POST的递归匹配
                                    if group in ["GET Matches", "POST Matches"] and group_idx == 2:
                                        extracted = extract_first_string(raw_value)
                                        if extracted:
                                            matched_results[group].append((extracted, label, file))
                                    else:
                                        matched_results[group].append((raw_value, label, file))
                                
                                except IndexError:
                                    continue  # 忽略无效的组索引
            except Exception as e:
                print(f"无法读取文件 {file_path}: {e}")

# 将结果写入 path.txt 文件
try:
    with open(output_file, 'w', encoding='utf-8') as f:
        for group, results in matched_results.items():
            if results:
                f.write(f"===== {group} =====\n")
                # 去重、排序并对齐
                unique_results = sorted(set(results), key=lambda x: (x[0], x[2]))  # 按路径和文件名排序
                
                # 计算各列最大宽度
                max_path_len = max(len(item[0]) for item in unique_results) if unique_results else 0
                max_label_len = max(len(item[1]) for item in unique_results) if unique_results else 0
                
                # 写入格式化结果
                for path, label, filename in unique_results:
                    f.write(f"{path.ljust(max_path_len)}\t{label.ljust(max_label_len)}\t{filename}\n")
                f.write("\n")  # 分块之间加空行
    print(f"匹配的路径已按分类写入 {output_file}")
except Exception as e:
    print(f"无法写入文件 {output_file}: {e}")