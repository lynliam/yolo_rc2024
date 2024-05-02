import os  #导入模块

filename_img = r"J:\yolov5-master\猫猫\cat_12_train" #图像文件地址
filename_lab = "J:/yolov5-master/wtr_first6000/datasets/labels/train_1500bk" #标签文件地址
list_patha_img = os.listdir(filename_img)   #读取文件夹里面的名字
list_patha_lab = os.listdir(filename_lab)   #读取文件夹里面的名字


count = 0
for index_img, index_lab in list_patha_img, list_patha_lab:
    if index_img == index_lab:
        path_img = filename_img + '\\' + index_img  # 原本文件名
        path_lab = filename_lab + '\\' + index_lab  # 原本文件名
        new_path_img = filename_img + '\\' + f'cat_{count}.txt'
        new_path_lab = filename_lab + '\\' + f'cat_{count}.txt'
        print(new_path_img, new_path_lab)
        os.rename(path_img, new_path_lab)
        os.rename(path_lab, new_path_lab)
        count += 1
    else:
        count += 1
        continue

'''
count = 0
for index in list_path:
    path = filename + '\\' + index  # 原本文件名
    new_path = filename + '\\' + f'color_{count}.txt'
    print(new_path)
    os.rename(path, new_path)
    count += 1
'''
