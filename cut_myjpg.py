import os
import shutil

# 源文件夹路径
source_folder = "J:\\yolov5-master\\wtr_first6000\\datasets\\images\\train_old6600"

# 目标文件夹路径
destination_folder = "J:/yolov5-master/wtr_first6000/datasets/images/tryimg"

# 获取文件列表
file_list = sorted(os.listdir(source_folder))

# 每隔两个文件复制一个，以使总文件数为原来的 1/3
total_files = len(file_list)

for i in range(0, total_files, 3):
    file_to_copy = os.path.join(source_folder, file_list[i])
    shutil.copy(file_to_copy, destination_folder)
