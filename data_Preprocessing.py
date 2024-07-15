import os
import pandas as pd
import re

def get_frequency_from_filename(filename):
    match = re.search(r'(\d+)', filename)
    if match:
        return f'{match.group(1)}min'
    return '5min'  # 默认值

def convert_and_fill_data(input_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    for filename in os.listdir(input_folder):
        if filename.endswith('.csv'):
            file_path = os.path.join(input_folder, filename)
            try:
                freq = get_frequency_from_filename(filename)
                
                # 读取CSV文件
                df = pd.read_csv(file_path)
                
                # 将时间列转换为datetime对象
                df['time'] = pd.to_datetime(df['time'], unit='s')
                
                # 设置时间列为索引
                df.set_index('time', inplace=True)
                
                # 对数据进行重采样，使用指定的频率
                df = df.resample(freq).agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last'
                }).dropna(how='all')  # 删除全为NaN的行
                
                # 重置索引，将时间列重新作为普通列
                df.reset_index(inplace=True)
                
                # 保存处理后的数据到输出文件夹
                output_file_path = os.path.join(output_folder, filename)
                df.to_csv(output_file_path, index=False, date_format='%Y/%m/%d %H:%M')
                
                print(f'成功处理 {filename}，数据清洗成功')
            
            except Exception as e:
                print(f'{filename} 数据清洗遇到问题: {e}')

# 使用示例
input_folder = 'original'
output_folder = 'data'
convert_and_fill_data(input_folder, output_folder)