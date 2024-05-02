import pandas as pd

# 读取 YOLOv5 输出的结果文件
result_file_path = 'path/to/yolov5_results.txt'

# 创建一个空的 DataFrame 用于存储目标检测结果
columns = ['image_path', 'detection_result']
df = pd.DataFrame(columns=columns)

# 解析 YOLOv5 输出的结果文件
with open(result_file_path, 'r') as file:
    lines = file.readlines()
    for line in lines:
        data = line.strip().split()
        image_path = data[0]
        detection_result = int(data[1])  # 假设检测结果是一个整数

        df = df.append({
            'image_path': image_path,
            'detection_result': detection_result
        }, ignore_index=True)

# 将 DataFrame 保存为 CSV 文件
output_csv_path = 'path/to/output_results.csv'
df.to_csv(output_csv_path, index=False)

print(f"CSV file saved at: {output_csv_path}")
