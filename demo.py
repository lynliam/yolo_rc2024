import os

def rename_images(file_path):
    with open(file_path) as f:
        lines = f.readlines()

    # 初始化标签计数器的字典
    label_counter = {}

    for line in lines:
        # 分割每一行的内容
        img_path, label = line.strip().split('\t')

        # 如果标签不在计数器字典中，将其加入并初始化计数为1
        if label not in label_counter:
            label_counter[label] = 1

        # 获取原始文件的路径和新的文件路径
        old_path = os.path.join(os.path.dirname(file_path), img_path)
        new_name = f"{label}_{label_counter[label]}.jpg"
        new_path = os.path.join(os.path.dirname(file_path), new_name)
        print(new_name)
        # 重命名文件
        os.rename(old_path, new_path)

        # 更新标签计数器
        label_counter[label] += 1

# 使用示例
rename_images('train_list.txt')


