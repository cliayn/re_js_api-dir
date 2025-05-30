import os
import re

# 定义匹配的正则表达式和分类标签
pattern_groups = {
    "PagePath Matches": [
        (re.compile(r'pagePath:\s*"(.*?)"'), "pagePath_double_quotes"),
        (re.compile(r"pagePath:\s*'(.*?)'"), "pagePath_double_quotes"),
    ],
    "Path Matches": [
        (re.compile(r'path:\s*"(.*?)"'), "path_double_quotes"),
        (re.compile(r"path:\s*'(.*?)'"), "path_double_quotes"),
        (re.compile(r'url:\s*"([^"]+)"'), "path_double_quotes"),
        (re.compile(r'url: "([^"]+)'), "path_double_quotes"),
    ],
    "GET Matches": [
        (re.compile(r'get\([^()]*?"([^"]*?)"[^()]*?\)'), "get_double_quotes"),
        (re.compile(r"get\([^()]*?['\"]([^'\"]*?)['\"][^()]*?\)"), "get_double_quotes"),
    ],
    "POST Matches": [
        (re.compile(r'post\([^()]*?"([^"]*?)"[^()]*?\)'), "post_double_quotes"),
        (re.compile(r"POST\([^()]*?['\"]([^'\"]*?)['\"][^()]*?\)"), "post_double_quotes"),
    ]
}

# 定义要遍历的目录
api_js_directory = "D:\Desktop\杂项\缴费"
output_file = "D:\Desktop\杂项\缴费\path.txt"

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
                                    # 按分组保存匹配的路径和标签
                                    matched_results[group].append((match, label))
            except Exception as e:
                print(f"无法读取文件 {file_path}: {e}")

# 将结果写入 path.txt 文件
try:
    with open(output_file, 'w', encoding='utf-8') as f:
        for group, results in matched_results.items():
            if results:
                f.write(f"===== {group} =====\n")
                # 去重、排序并对齐
                unique_results = sorted(set(results), key=lambda x: x[0])
                max_length = max(len(path) for path, _ in unique_results)
                for path, label in unique_results:
                    f.write(f"{path.ljust(max_length)}\t{label}\n")
                f.write("\n")  # 分块之间加空行
    print(f"匹配的路径已按分类写入 {output_file}")
except Exception as e:
    print(f"无法写入文件 {output_file}: {e}")
