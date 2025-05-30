import argparse  # python的命令行解析的标准模块  可以让我们直接在命令行中就可以向程序中传入参数并让程序运行
import os
import shutil
import time
from pathlib import Path  # Path将str转换为Path对象 使字符串路径易于操作的模块

import cv2
import torch
import torch.backends.cudnn as cudnn  # cuda模块
from numpy import random
import numpy as np
import pyrealsense2 as rs  # 导入realsense的sdk模块
import coordinate_transformation  # 坐标转换模块

from models.experimental import attempt_load
from utils.general_grasp import (
    check_img_size, non_max_suppression, apply_classifier, scale_coords,
    xyxy2xywh, plot_one_box, strip_optimizer, set_logging)
from utils.torch_utils import select_device, load_classifier, time_synchronized
from utils.datasets import letterbox


def detect(save_img=False):
    # 加载参数
    out, source, weights, view_img, save_txt, imgsz = \
        opt.save_dir, opt.source, opt.weights, opt.view_img, opt.save_txt, opt.img_size
    webcam = source == '0' or source.startswith(('rtsp://', 'rtmp://', 'http://')) or source.endswith('.txt')

    # 初始化
    set_logging()  # 生成日志
    device = select_device(opt.device)  # 获取当前主机可用的设备
    if os.path.exists(out):  # output dir
        shutil.rmtree(out)  # delete dir
    os.makedirs(out)  # make new dir
    # 如果设配是GPU 就使用half(float16)  包括模型半精度和输入图片半精度
    half = device.type != 'cpu'  # half precision only supported on CUDA

    # 载入模型和模型参数并调整模型
    model = attempt_load(weights, device=device)  # 加载Float32模型
    imgsz = check_img_size(imgsz, s=model.stride.max())  # 确保输入图片的尺寸imgsz能整除stride=32 如果不能则调整为能被整除并返回
    if half:  # 是否将模型从float32 -> float16  加速推理
        model.half()  # to FP16

    # 加载推理数据
    vid_path, vid_writer = None, None
    # 采用webcam数据源
    view_img = True
    cudnn.benchmark = True  # 加快常量图像大小推断
    # dataset = LoadStreams(source, img_size=imgsz)  #load 文件夹中视频流

    # 获取每个类别的名字和随机生成类别颜色
    names = model.module.names if hasattr(model, 'module') else model.names
    colors = [[random.randint(0, 255) for _ in range(3)] for _ in range(len(names))]

    # 正式推理
    t0 = time.time()  # 记录时间
    # 初始化一个全0tensor进行一次正向推理
    img = torch.zeros((1, 3, imgsz, imgsz), device=device)
    _ = model(img.half() if half else img) if device.type != 'cpu' else None  # run once

    # 实例化realsense模块
    # https://www.rs-online.com/designspark/intelpython2-nvidia-jetson-nanorealsense-d435-cn
    pipeline = rs.pipeline()
    # 创建 config 对象：
    config = rs.config()
    # 声明RGB和深度视频流
    # config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

    # 启动数据流
    pipeline.start(config)
    align_to_color = rs.align(rs.stream.color)  # 对齐rgb和深度图
    while True:
        start = time.time()
        # Wait for a coherent pair of frames（一对连贯的帧）: depth and color
        frames = pipeline.wait_for_frames()  # 等待最新的影像，wait_for_frames返回的是一個合成的影像
        frames = align_to_color.process(frames)  # 将上图获取视频帧对齐
        # 使用 process 來實現剛剛宣告的 align 對齊功能
        # 将合成帧分开
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        # 转换成 numpy 数据
        color_image = np.asanyarray(color_frame.get_data())
        depth_image = np.asanyarray(depth_frame.get_data())
        mask = np.zeros([color_image.shape[0], color_image.shape[1]], dtype=np.uint8)
        mask[0:480, 320:640] = 255

        # 对RGB的img进行处理，送入预测模型
        sources = [source]  # 数据源
        imgs = [None]
        path = sources  # path: 图片/视频的路径
        imgs[0] = color_image
        im0s = imgs.copy()  # img0s: 原尺寸的图片
        img = [letterbox(x, new_shape=imgsz)[0] for x in im0s]  # img: 进行resize + pad之后的图片
        img = np.stack(img, 0)  # 沿着0dim进行堆叠
        img = img[:, :, :, ::-1].transpose(0, 3, 1, 2)  # BGR to RGB, to 3x416x416, uint8 to float32
        img = np.ascontiguousarray(img, dtype=np.float16 if half else np.float32)
        # ascontiguousarray函数将一个内存不连续存储的数组转换为内存连续存储的数组，使得运行速度更快。
        img /= 255.0  # 0 - 255 to 0.0 - 1.0

        # 处理每一张图片的数据格式
        img = torch.from_numpy(img).to(device)  # 将numpy转为pytorch的tensor,并转移到运算设备上计算
        # 如果图片是3维(RGB) 就在前面添加一个维度1当中batch_size=1
        # 因为输入网络的图片需要是4为的 [batch_size, channel, w, h]
        if img.ndimension() == 3:
            img = img.unsqueeze(0)  # 在dim0位置添加维度1，[channel, w, h] -> [batch_size, channel, w, h]
        t1 = time_synchronized()  # 精确计算当前时间  并返回当前时间
        # 对每张图片/视频进行前向推理
        pred = model(img, augment=opt.augment)[0]

        # 进行NMS
        # conf_thres: 置信度阈值
        # iou_thres: iou阈值
        # classes: 是否只保留特定的类别 默认为None
        # agnostic_nms: 进行nms是否也去除不同类别之间的框 默认False
        # max_det: 每张图片的最大目标个数 默认1000
        # pred: [num_obj, 6] = [5, 6]   这里的预测信息pred还是相对于 img_size(640) 的
        pred = non_max_suppression(pred, opt.conf_thres, opt.iou_thres, classes=opt.classes, agnostic=opt.agnostic_nms)
        t2 = time_synchronized()

        # 后续保存或者打印预测信息
        for i, det in enumerate(pred):  # detections per image
            p, s, im0 = path[i], '%g: ' % i, im0s[i].copy()
            s += '%gx%g ' % img.shape[2:]  # print string
            gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
            if det is not None and len(det):
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()

                # Print results
                for c in det[:, -1].unique():
                    n = (det[:, -1] == c).sum()  # detections per class
                    s += '%g %ss, ' % (n, names[int(c)])  # add to string

                # Write results
            for *xyxy, conf, cls in reversed(det):
                    xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # 归一化为 xywh
                    line = (cls, conf, *xywh) if opt.save_conf else (cls, *xywh)  # label format
                    # 获取距离信息
                    distance_list = []
                    mid_pos = [int((int(xyxy[0]) + int(xyxy[2])) / 2),
                               int((int(xyxy[1]) + int(xyxy[3])) / 2)]  # 获得预测框的中心像素位置
                    # print(f'x= {int((int(xyxy[0]) + int(xyxy[2])) / 2)}')
                    u = int((int(xyxy[0]) + int(xyxy[2])) / 2)  # 物体中心的像素坐标u，v
                    v = int((int(xyxy[1]) + int(xyxy[3])) / 2)
                    # coordinate_transformation.
                    min_val = min(abs(int(xyxy[2]) - int(xyxy[0])), abs(int(xyxy[3]) - int(xyxy[1])))  # 确定偏差搜索范围
                    # print(box,)
                    # 声明一个num为40的随机序列，同一目标预测框每个序号生成一个深度值
                    randnum = 40
                    for i in range(randnum):
                        bias = random.randint(-min_val // 4, min_val // 4)  # 生成固定范围内的随机整数为偏差,'//'整数除法
                        dist = depth_frame.get_distance(int(mid_pos[0] + bias),
                                                        int(mid_pos[1] + bias))  # 从深度视频帧中获得目标点的深度信息
                        # print(int(mid_pos[1] + bias), int(mid_pos[0] + bias))
                        if dist:
                            distance_list.append(dist)  # 添加到列表
                    # 将40个深度数据进行处理
                    distance_list = np.array(distance_list)
                    distance_list = np.sort(distance_list)[
                                    randnum // 2 - randnum // 4:randnum // 2 + randnum // 4]  # 冒泡排序实现中值滤波
                    depth_dis = np.mean(distance_list) * 1000  # 最后取平均值为目标深度,单位为mm
                    # 相机坐标系：Xc = {result_dot[0][0]},Yc = {result_dot[1][0]},Zc = {result_dot[2][0]}
                    # 相机内参：fx, fy, u0, v0   (u,v)：像素坐标   depth_dis:深度值cm
                    fx, fy, u0, v0 = 609.0341796875, 609.1449584960938, 326.2749938964844, 240.2576904296875
                    result_dot = coordinate_transformation.change_3d(u, v, depth_dis, fx, fy, u0, v0)  # 返回[[Xc],[Yc],[Zc]]
                    # Xc = result_dot[0][0] / 10
                    # Yc = result_dot[1][0] / 10
                    # Zc = result_dot[2][0] / 10  # 相机坐标系下的三维坐标,单位：cm
                    Xc = "{:.2f}".format(result_dot[0][0] / 10)
                    Yc = "{:.2f}".format(result_dot[1][0] / 10)
                    Zc = "{:.2f}".format(result_dot[2][0] / 10)
                    print(f'相机坐标系：Xc = {Xc}cm,Yc = {Yc}cm,Zc = {Zc}cm')
                    # ------------相机坐标转换机械手基底坐标--------------------------------------

                    # label = '%s' % (names[int(cls)])
                    label = '%s %.2f%s' % (names[int(cls)], conf * 100, '%')
                    plot_one_box(xyxy, im0, Xc, Yc, Zc, label=label, color=colors[int(cls)], line_thickness=3)
                    # annotator.box_label(xyxy, label, color=colors[int(cls)])

                # 将结果框打印回原图

            # Print time (inference + NMS)
            print('%sDone. (%.3fs)' % (s, t2 - t1))

            # Stream results
            if view_img:
                cv2.imshow(p, im0)
                if cv2.waitKey(1) == ord('q'):  # q to quit
                    raise StopIteration
        print('Done. (%.3fs)' % (time.time() - t0))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default='yolov5s.pt', help='model.pt path(s)')
    # parser.add_argument('--weights', nargs='+', type=str,
    #                     default='/home/user/cxking/project/yolo/yolov5/runs/train/exp2/weights/best.pt',
    #                     help='model.pt path(s)')
    parser.add_argument('--source', type=str, default='0', help='source')  # file/folder, 0 for webcam
    parser.add_argument('--img-size', type=int, default=640, help='inference size (pixels)')
    parser.add_argument('--conf-thres', type=float, default=0.1, help='object confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.1, help='IOU threshold for NMS')
    parser.add_argument('--device', default='0', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--view-img', action='store_true', help='display results')
    parser.add_argument('--save-txt', action='store_true', help='save results to *.txt')
    parser.add_argument('--save-conf', action='store_true', help='save confidences in --save-txt labels')
    parser.add_argument('--save-dir', type=str, default='inference/output', help='directory to save results')
    parser.add_argument('--classes', nargs='+', type=int, help='filter by class: --class 0, or --class 0 2 3')
    parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    parser.add_argument('--augment', action='store_true', help='augmented inference')
    parser.add_argument('--update', action='store_true', help='update all models')
    opt = parser.parse_args()
    print(opt)

    with torch.no_grad():  # 一个上下文管理器，被该语句wrap起来的部分将不会track梯度
        detect()
