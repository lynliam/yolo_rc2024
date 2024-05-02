import os  #导入模块

filename_list = r"C:\Users\86139\Desktop\train_list.txt" #train_list 地址
list_patha_img = os.listdir(filename_img)   #读取文件夹里面的名字

count = 0
for index_img in list_patha_img:
	path_img = filename_img + '\\' + index_img  # 原本文件名
	new_path_img = filename_img + '\\' + f'cat_{count}.jpg'
	print(new_path_img)
	os.rename(path_img, new_path_img)
	count += 1