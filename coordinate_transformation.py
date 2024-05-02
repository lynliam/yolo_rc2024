import numpy as np
#
# Zc = 100  # 单位：mm
# u, v = 11, 10  # 像素坐标


# 像素坐标转换到相机坐标系下坐标 ;相机内参：fx, fy, u0, v0 ,(u,v)：像素坐标,depth_dis:深度值cm
def change_3d(u, v, Zc, fx, fy, u0, v0):
    # 函数体
    # 内参赋值和深度值
    # fx, fy, u0, v0 = 1, 1, 1, 1

    # 创建矩阵
    pixel_coordinates = np.array([[u], [v], [1]])
    matrix = np.array([[fx, 0, u0], [0, fy, v0], [0, 0, 1]])  # 内参矩阵

    det = np.linalg.det(matrix)

    if det != 0:
        print("相机内参矩阵可逆，行列式为", det)
        # 求解矩阵的逆
        inverse_matrix = np.linalg.inv(matrix)

        # print("原始矩阵:\n", matrix)
        # print("逆矩阵:\n", inverse_matrix)
        # 矩阵转换获得相机坐标系下的三维坐标[Xc,Yc,Zc]
        # 使用np.dot进行矩阵相乘
        result_dot = Zc * np.dot(inverse_matrix, pixel_coordinates)
        return result_dot  # 返回[[Xc],[Yc],[Zc]]
    else:
        print("矩阵不可逆，相机内参有误")

# 手眼标定，相机坐标系转换到机械臂基底坐标系
def change_robot(Xc, Yc, Zc):
    pass
