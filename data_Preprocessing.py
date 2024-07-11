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

                chunks = pd.read_csv(file_path, chunksize=10000)

                df_list = []
                for chunk in chunks:
                    chunk['time'] = pd.to_datetime(chunk['time'], unit='s')
                    df_list.append(chunk)
                
                df = pd.concat(df_list)
                df.set_index('time', inplace=True)

                # 生成完整的时间范围
                all_times = pd.date_range(start=df.index.min(), end=df.index.max(), freq=freq)

                # 重新索引并填充缺失数据
                df = df.reindex(all_times).ffill()

                # 删除除 open, high, low, close 外的其他列
                df = df[['open', 'high', 'low', 'close']]

                # 添加日期标题
                df.reset_index(inplace=True)
                df.rename(columns={'index': 'time'}, inplace=True)

                # 保存处理后的数据到输出文件夹
                output_file_path = os.path.join(output_folder, filename)
                df.to_csv(output_file_path, index=False, date_format='%Y/%m/%d %H:%M')

                print(f'成功处理 {filename}，数据清洗成功')

            except Exception as e:
                print(f'{filename} 数据清洗遇到 {e} 问题')

# 使用示例
input_folder = 'original'
output_folder = 'data'
convert_and_fill_data(input_folder, output_folder)
