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

def load_data(file_path):
    try:
        df = pd.read_csv(file_path)
        logging.info(f"文件 {file_path} 的列: {df.columns}")
        if 'time' not in df.columns:
            logging.error(f"文件 {file_path} 缺少'time'列")
            return pd.DataFrame()

        df['datetime'] = df['time'].apply(convert_time)
        df = df.dropna(subset=['datetime'])
        df.set_index('datetime', inplace=True)
        logging.info(f"加载的数据: {df.head()}")
        return df
    except Exception as e:
        logging.error(f"加载数据文件 {file_path} 时出错: {str(e)}")
        return pd.DataFrame()

def preprocess_data(df, filename):
    try:
        freq = get_frequency_from_filename(filename)
        df = df.resample(freq).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'atr': 'last'
        }).ffill()
        df = df[df['volume'] != 0]
        df = df.dropna()
        df.reset_index(inplace=True)
        logging.info(f"预处理后的数据: {df.head()}")
        return df
    except Exception as e:
        logging.error(f"预处理数据时出错: {str(e)}")
        return pd.DataFrame()

def save_processed_data(df, filename):
    output_path = os.path.join('processed', filename)
    try:
        df.to_csv(output_path, index=False)
        logging.info(f"保存预处理数据到 {output_path}")
    except Exception as e:
        logging.error(f"保存数据文件 {output_path} 时出错: {str(e)}")

def process_all_files(data_dir):
    for filename in os.listdir(data_dir):
        if filename.endswith('.csv'):
            file_path = os.path.join(data_dir, filename)
            df = load_data(file_path)
            if not df.empty:
                df.name = filename  # 用于获取频率
                processed_df = preprocess_data(df, filename)
                save_processed_data(processed_df, filename)

if __name__ == "__main__":
    data_directory = 'data'
    process_all_files(data_directory)
