import os
import re
import regex

# 定义匹配的正则表达式和分类标签
pattern_groups = {
    "PagePath Matches": [
        (re.compile(r"(?i)pagePath:\s*[\"'](.*?)[\"']"), "pagePath")
    ],
    "Path Matches": [
        (re.compile(r"(?i)path:\s*[\"'](.*?)[\"']"), "path"),
        (re.compile(r"(?i)url:\s*[\"']([^\"']+)[\"']"), "url"),
        (re.compile(r"(?i)name:\s*[\"']([^\"']+)[\"']"), "name"),
    ],
    "GET Matches": [
        (re.compile(r"(?i)get\([^()]*?['\"]([^'\"]*?)['\"][^()]*?\)"), ""),
        (re.compile(r"(?i)url:['\"]([^'\"]+)['\"],\s*method:\s*['\"]get['\"]"), ""),
    ],
    "POST Matches": [
        (re.compile(r"(?i)post\([^()]*?['\"]([^'\"]*?)['\"][^()]*?\)"), ""),
        (re.compile(r"(?i)url:['\"]([^'\"]+)['\"],\s*method:\s*['\"]post['\"]"), ""),
    ],
    "Object": [
        (re.compile(r'\b[a-zA-Z][a-zA-Z0-9]*\b:\[\{\s*\b[a-zA-Z][a-zA-Z0-9]*\b:""'), "")
    ]
}

# 定义要遍历的目录
api_js_directory = "js"
output_file = "path.txt"

# 初始化结果存储
matched_results = {group: [] for group in pattern_groups}

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
                        for pattern, label in patterns:
                            matches = pattern.findall(content)
                            if matches:
                                for match in matches:
                                    # 按分组保存匹配的路径、标签和文件名
                                    matched_results[group].append((match, label, file))
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
                max_path_len = max(len(item[0]) for item in unique_results)
                max_label_len = max(len(item[1]) for item in unique_results)
                
                # 写入格式化结果
                for path, label, filename in unique_results:
                    f.write(f"{path.ljust(max_path_len)}\t{label.ljust(max_label_len)}\t{filename}\n")
                f.write("\n")  # 分块之间加空行
    print(f"匹配的路径已按分类写入 {output_file}")
except Exception as e:
    print(f"无法写入文件 {output_file}: {e}")