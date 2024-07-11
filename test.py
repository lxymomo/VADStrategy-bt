import pandas as pd
import backtrader as bt

# 测试读取 CSV 文件并打印内容
def test_read_csv(file_path):
    try:
        # 打印前几行数据，验证读取是否正确
        df = pd.read_csv(file_path)
        print("前几行数据:")
        print(df.head())

        # 检查每行的列数是否一致
        expected_columns = 5  # 包括 time, open, high, low, close
        for i, row in df.iterrows():
            if len(row) != expected_columns:
                print(f"Row {i} has {len(row)} columns: {row}")

        # 使用 GenericCSVData 读取数据
        print("使用 GenericCSVData 读取数据")
        data = bt.feeds.GenericCSVData(
            dataname=file_path,
            dtformat='%Y/%m/%d %H:%M',
            datetime=0,
            open=1,
            high=2,
            low=3,
            close=4,
            volume=-1,  # 如果没有 volume 列，设置为 -1
            openinterest=-1,  # 如果没有 openinterest 列，设置为 -1
            separator=',',  # 指定分隔符
        )
        
        cerebro = bt.Cerebro()
        cerebro.adddata(data)
        
        # 运行回测，打印数据
        print("运行回测并打印数据")
        cerebro.run(runonce=False, preload=False)
    except Exception as e:
        print(f"Error reading CSV file: {e}")

# 测试文件路径
file_path = 'data/BATS_QQQ_5.csv'
test_read_csv(file_path)
