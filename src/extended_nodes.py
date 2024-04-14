from flow_nodes import Executor
from utils.util import read_file, read_text_file_list, read_text_files
import os
import re
import json

ZFILL_NUM = 4

class Splitter(Executor):
    def __init__(self, node):
        super().__init__(node, None )

    def execute(self, output_dir):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for parameter in self.node["input_parameters"]:
            if parameter["type"] == "file" and parameter["name"] == "source_file":
                input_path = parameter["file_path"]
            elif parameter["type"] == "int" and parameter["name"] == "max_length":
                max_length = parameter["value"]

        if not input_path:
            print("Error: input_path is not specified.")
            exit(0)

        outputs = self.node["output"]

        for output_item in outputs:
            if output_item["type"] == "file_list":
                output_file_path = os.path.join(output_dir, output_item["name"])

        content = read_file(input_path)

        paragraphs = self.split_paragraphs(content)

        current_file = 0
        current_length = 0
        grouped_paragraphs = []

        # Get the folder path
        folder_path = os.path.dirname(output_file_path)
        # Check if the folder exists, if not, create it
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        if max_length > 0:
            for paragraph in paragraphs:
                paragraph_length = len(paragraph["content"])
                paragraph_type = paragraph["type"]

                if paragraph_type == "code":
                    if len(grouped_paragraphs) > 0:
                        current_file += 1
                        self.print_splited_content(current_file, output_file_path, grouped_paragraphs)
                        grouped_paragraphs = []
                        current_length = 0

                    current_file += 1
                    self.print_splited_content(current_file, output_file_path, [paragraph])

                elif paragraph_type == "text":
                    if current_length + paragraph_length + 1 >= max_length:  # +1 是为了考虑换行符
                        # 将当前组合的文本保存到一个新文件中
                        if len(grouped_paragraphs) > 0:
                            current_file += 1
                            self.print_splited_content(current_file, output_file_path, grouped_paragraphs)

                            current_length = 0
                            grouped_paragraphs = []

                    grouped_paragraphs.append(paragraph)
                    current_length += paragraph_length + 1

            # 保存最后一个输出文件（如果有内容）
            if len(grouped_paragraphs) > 0:
                current_file += 1
                self.print_splited_content(current_file, output_file_path, grouped_paragraphs)

        elif max_length == 0:
            for paragraph in paragraphs:
                current_file += 1
                self.print_splited_content(current_file, output_file_path, [paragraph])
        elif max_length == -1:
            self.print_splited_content(0, output_file_path, paragraphs)
        else:
            print("Error: max_length is not specified.")
            exit(0)

        return

    def print_splited_content(self, current_file_no, output_file_path, grouped_paragraphs):
        real_output_file_path = output_file_path.replace("${i}", str(current_file_no).zfill(ZFILL_NUM))
        if len(grouped_paragraphs) == 1:
            with open(real_output_file_path, 'w', encoding='utf-8') as output_file:
                json_paragraph = json.dumps(grouped_paragraphs[0], ensure_ascii=False)
                output_file.write(json_paragraph)
        else:
            if len(grouped_paragraphs) == 0:
                return

            type = grouped_paragraphs[0]["type"]
            content = ""
            for paragraph in grouped_paragraphs:
                if paragraph["type"] != type:
                    type = "mixed"
                content += paragraph["content"] + '\n'

            output_obj = {"type": type, "content": content}
            with open(real_output_file_path, 'w', encoding='utf-8') as output_file:
                json_paragraph = json.dumps(output_obj)
                output_file.write(json_paragraph)
        return

    def split_paragraphs(self, content):
        code_blocks = re.split(r'(```.*?```)', content, flags=re.DOTALL)
        paragraphs = []
        for block in code_blocks:
            if block.startswith('```') and block.endswith('```'):
                # This is a code block, treat it as a single paragraph
                paragraphs.append({"type": "code", "content": block})
            else:
                # This is a non-code block, split it into paragraphs by newline characters
                text_paragraphs = block.split('\n')
                for text_paragraph in text_paragraphs:
                    if text_paragraph.strip():
                        paragraphs.append({"type": "text", "content": text_paragraph})
        return paragraphs

class Merger(Executor):
    def __init__(self, node):
        super().__init__(node, None)

    def execute(self, output_dir):

        for parameter in self.node["input_parameters"]:
            if parameter["type"] == "file_list" and parameter["name"] == "rewritten_data":
                input_file_path = parameter["file_path"]

        merged_file_names, all_contents = read_text_file_list(input_file_path)

        outputs = self.node["output"]

        for output_item in outputs:
            if output_item["type"] == "file":
                output_file_path = os.path.join(output_dir, output_item["name"])

        separator = ""
        ignored_content = None
        if "additional_info" in self.node:
            separator = self.node["additional_info"]["separator"]
            if "ignored_content" in self.node["additional_info"]:
                ignored_content = self.node["additional_info"]["ignored_content"]

        grouped_by = ""

        if "${i}" in output_file_path and "${j}" in output_file_path:
            print("Error: It is invalid that both ${i} and ${j} are in the output_file_path. Only one variable index is allowed.")
            return
        elif "${i}" in output_file_path:
            grouped_by = "${i}"
        elif "${j}" in output_file_path:
            grouped_by = "${j}"

        index_part_set = set()
        file_groups_dict = dict()
        # New code:
        pattern = re.compile(r'^(.+?)_(\d{4})_(\d{4})\.txt$')
        for file_name in merged_file_names:
            match = pattern.match(file_name)
            if match:
                file_basename, i, j = match.groups()
                if grouped_by == "${i}":
                    index_part_set.add(i)
                    if i in file_groups_dict.keys():
                        file_groups_dict[i].append(file_name)
                    else:
                        file_groups_dict[i] = [file_name]
                elif grouped_by == "${j}":
                    index_part_set.add(j)
                    if j in file_groups_dict.keys():
                        file_groups_dict[j].append(file_name)
                    else:
                        file_groups_dict[j] = [file_name]

        item_in_group_number = 0
        if not file_groups_dict:
            file_groups_dict[""] = all_contents
            item_in_group_number = len(all_contents)
        else:
            for key in file_groups_dict.keys():
                file_paths = file_groups_dict[key]
                texts = read_text_files(file_paths)
                file_groups_dict[key] = texts
                item_in_group_number = len(texts)

        index = 0
        for key in file_groups_dict.keys():
            merged_content = file_groups_dict[key]
            real_output_file_path = output_file_path.replace(grouped_by, key)
            # Write the merged content to the output_path
            with open(real_output_file_path, 'w', encoding="utf-8") as f:
                for content in merged_content:
                    if not ignored_content or content != ignored_content:
                        if index >= item_in_group_number:
                            index = 0
                        index += 1
                        if separator and "${index}" in separator:
                            new_separator = separator.replace("${index}", str(index))
                        else:
                            new_separator = separator
                        f.write(new_separator + content + "\n")
        return