import os
import pandas as pd
import re
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_frequency_from_filename(filename):
    match = re.search(r'(\d+)', filename)
    if match:
        return f'{match.group(1)}min'
    return '5min'  # 默认值

def convert_time(time_str):
    try:
        return pd.to_datetime(time_str, format='%Y/%m/%d %H:%M')
    except ValueError as e:
        logging.error(f"无法解析时间字符串: {time_str}. 错误: {str(e)}")
        return pd.NaT

def convert_and_fill_data(input_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    required_columns = ['time', 'open', 'high', 'low', 'close', 'volume', 'atr']
    
    for filename in os.listdir(input_folder):
        if filename.endswith('.csv'):
            file_path = os.path.join(input_folder, filename)
            try:
                logging.info(f"开始处理文件: {filename}")
                freq = get_frequency_from_filename(filename)
                
                # 读取CSV文件
                df = pd.read_csv(file_path)
                logging.info(f"原始数据形状: {df.shape}")
                
                # 检查必需的列是否都存在
                if not all(col in df.columns for col in required_columns):
                    missing_cols = [col for col in required_columns if col not in df.columns]
                    logging.error(f"文件 {filename} 缺少以下列: {missing_cols}")
                    continue
                
                # 转换时间列
                df['datetime'] = df['time'].apply(convert_time)
                df = df.dropna(subset=['datetime'])
                logging.info(f"时间转换后数据形状: {df.shape}")
                
                # 设置时间列为索引
                df.set_index('datetime', inplace=True)
                
                # 对数据进行重采样和填充
                df = df.resample(freq).agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum',
                    'atr': 'last'
                }).ffill()  # 使用前向填充
                logging.info(f"重采样和填充后数据形状: {df.shape}")
                
                # 过滤 volume 为 0 的记录
                df = df[df['volume'] != 0]
                
                # 删除包含任何 NaN 的行
                df = df.dropna()
                logging.info(f"删除NaN行后数据形状: {df.shape}")
                
                # 重置索引，将时间列重新作为普通列
                df.reset_index(inplace=True)

                # 确保列的顺序符合 backtrader 的默认期望
                df = df[['datetime', 'open', 'high', 'low', 'close', 'volume', 'atr']]
                
                if df.empty:
                    logging.warning(f"处理后 {filename} 没有数据")
                    continue
                
                # 保存处理后的数据到输出文件夹
                output_file_path = os.path.join(output_folder, filename)
                df.to_csv(output_file_path, index=False, date_format='%Y/%m/%d %H:%M')
                
                logging.info(f'成功处理 {filename}，数据清洗成功。最终数据形状: {df.shape}')
            
            except Exception as e:
                logging.error(f'{filename} 数据清洗遇到问题: {str(e)}')

# 使用示例
input_folder = 'data'
output_folder = 'processed'
convert_and_fill_data(input_folder, output_folder)