"""
参数化测试 - Excel数据处理模块
"""
import openpyxl
import csv
import json
import os
from werkzeug.utils import secure_filename


class DataSetParser:
    """数据集解析器"""

    # 允许的文件扩展名
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

    # 文件大小限制（5MB）
    MAX_FILE_SIZE = 5 * 1024 * 1024

    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate_file(self, file):
        """
        验证上传的文件

        返回: (is_valid, error_message)
        """
        if not file:
            return False, "未选择文件"

        # 检查文件名
        if file.filename == '':
            return False, "文件名为空"

        # 检查文件扩展名
        if not self._allowed_file(file.filename):
            return False, f"不支持的文件格式，仅支持: {', '.join(self.ALLOWED_EXTENSIONS)}"

        # 检查文件大小（如果可以获取）
        try:
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)

            if file_size > self.MAX_FILE_SIZE:
                return False, f"文件过大，最大支持 {self.MAX_FILE_SIZE / 1024 / 1024}MB"
        except:
            pass  # 无法获取文件大小，跳过检查

        return True, None

    def _allowed_file(self, filename):
        """检查文件扩展名是否允许"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS

    def parse_excel(self, file_path):
        """
        解析Excel文件

        返回: (success, data, error_message)
        data格式: [
            {'column1': 'value1', 'column2': 'value2'},
            ...
        ]
        """
        try:
            # 尝试打开Excel文件
            workbook = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            sheet = workbook.active

            # 读取表头（第一行）
            headers = []
            for cell in sheet[1]:
                if cell.value:
                    headers.append(str(cell.value).strip())
                else:
                    headers.append(f"Column_{len(headers) + 1}")

            if not headers:
                return False, [], "Excel文件为空或格式错误"

            # 读取数据行
            data = []
            for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                # 跳过空行
                if all(cell is None or str(cell).strip() == '' for cell in row):
                    continue

                # 构建数据字典
                row_data = {}
                for col_idx, (header, value) in enumerate(zip(headers, row)):
                    # 转换值为字符串，处理None
                    if value is None:
                        row_data[header] = ''
                    else:
                        row_data[header] = str(value).strip()

                data.append(row_data)

            workbook.close()

            if not data:
                return False, [], "Excel文件没有数据行"

            return True, data, None

        except Exception as e:
            return False, [], f"解析Excel文件失败: {str(e)}"

    def parse_csv(self, file_path):
        """
        解析CSV文件

        返回: (success, data, error_message)
        """
        try:
            data = []

            # 尝试不同的编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']
            content = None

            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except:
                    continue

            if content is None:
                return False, [], "无法读取CSV文件，编码格式不支持"

            # 解析CSV
            lines = content.splitlines()
            if not lines:
                return False, [], "CSV文件为空"

            # 尝试检测分隔符
            delimiter = ','
            if '\t' in lines[0]:
                delimiter = '\t'

            reader = csv.DictReader(lines, delimiter=delimiter)

            for row in reader:
                # 清理数据
                clean_row = {}
                for key, value in row.items():
                    clean_key = key.strip() if key else f"Column_{len(clean_row) + 1}"
                    clean_value = value.strip() if value else ''
                    clean_row[clean_key] = clean_value

                # 跳过空行
                if any(v for v in clean_row.values()):
                    data.append(clean_row)

            if not data:
                return False, [], "CSV文件没有数据行"

            return True, data, None

        except Exception as e:
            return False, [], f"解析CSV文件失败: {str(e)}"

    def parse_file(self, file_path):
        """
        自动识别并解析文件

        返回: (success, data, error_message)
        """
        file_ext = file_path.rsplit('.', 1)[1].lower()

        if file_ext in ['xlsx', 'xls']:
            return self.parse_excel(file_path)
        elif file_ext == 'csv':
            return self.parse_csv(file_path)
        else:
            return False, [], f"不支持的文件格式: {file_ext}"

    def validate_data(self, data):
        """
        验证数据格式

        返回: (is_valid, error_message)
        """
        if not data:
            return False, "数据为空"

        if not isinstance(data, list):
            return False, "数据格式错误"

        # 检查每行数据
        for idx, row in enumerate(data, start=1):
            if not isinstance(row, dict):
                return False, f"第{idx}行数据格式错误"

            if not row:
                return False, f"第{idx}行数据为空"

        return True, None

    def replace_variables(self, template, variables):
        """
        替换模板中的变量

        template: 模板字符串，如 "https://api.com/users/{{user_id}}"
        variables: 变量字典，如 {"user_id": "123"}

        返回: 替换后的字符串
        """
        if not template:
            return template

        result = template
        for key, value in variables.items():
            # 支持 {{variable}} 和 ${variable} 两种格式
            result = result.replace(f"{{{{{key}}}}}", str(value))
            result = result.replace(f"${{{key}}}", str(value))

        return result
