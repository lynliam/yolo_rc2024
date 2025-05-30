import argparse
import os
import platform
import random
import sys
from pathlib import Path

import torch
from torch.backends import cudnn

FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]  # YOLOv5 root directory
if str(ROOT) not in sys.path:
	sys.path.append(str(ROOT))  # add ROOT to PATH
ROOT = Path(os.path.relpath(ROOT, Path.cwd()))  # relative
from models.common import DetectMultiBackend
from utils.dataloaders import IMG_FORMATS, VID_FORMATS, MyLoadImages, LoadScreenshots, LoadStreams
from utils.general import (LOGGER, Profile, check_file, check_img_size, check_imshow, check_requirements, colorstr, cv2,
                           increment_path, non_max_suppression, print_args, scale_boxes, strip_optimizer, xyxy2xywh)
from utils.plots import Annotator, colors, save_one_box
from utils.torch_utils import select_device, smart_inference_mode, time_sync

"""
使用面向对象编程中的类来封装，需要去除掉原始 detect.py 中的结果保存方法，重写
保存方法将结果保存到一个 csv 文件中并打上视频的对应帧率
"""


class YoloOpt:
	def __init__(self, weights='weights/last.pt',
	             imgsz=(640, 640), conf_thres=0.25,
	             iou_thres=0.45, device='cpu', view_img=False,
	             classes=None, agnostic_nms=False,
	             augment=False, update=False, exist_ok=False,
	             project='/detect/result', name='result_exp',
	             save_csv=True):
		self.weights = weights  # 权重文件地址
		self.source = None  # 待识别的图像
		if imgsz is None:
			self.imgsz = (640, 640)
		self.imgsz = imgsz  # 输入图片的大小，默认 (640,640)
		self.conf_thres = conf_thres  # object置信度阈值 默认0.25  用在nms中
		self.iou_thres = iou_thres  # 做nms的iou阈值 默认0.45   用在nms中
		self.device = device  # 执行代码的设备，由于项目只能用 CPU，这里只封装了 CPU 的方法
		self.view_img = view_img  # 是否展示预测之后的图片或视频 默认False
		self.classes = classes  # 只保留一部分的类别，默认是全部保留
		self.agnostic_nms = agnostic_nms  # 进行NMS去除不同类别之间的框, 默认False
		self.augment = augment  # augmented inference TTA测试时增强/多尺度预测，可以提分
		self.update = update  # 如果为True,则对所有模型进行strip_optimizer操作,去除pt文件中的优化器等信息,默认为False
		self.exist_ok = exist_ok  # 如果为True,则对所有模型进行strip_optimizer操作,去除pt文件中的优化器等信息,默认为False
		self.project = project  # 保存测试日志的参数，本程序没有用到
		self.name = name  # 每次实验的名称，本程序也没有用到
		self.save_csv = save_csv  # 是否保存成 csv 文件，本程序目前也没有用到


class DetectAPI:
	def __init__(self, weights, imgsz=640):
		# 初始化参数，加载模型
		self.opt = YoloOpt(weights=weights, imgsz=imgsz)
		weights = self.opt.weights  # 传入的权重
		imgsz = self.opt.imgsz  # 传入的图像尺寸

		# Initialize 初始化
		# 获取设备 CPU/CUDA
		self.device = select_device(self.opt.device)
		# 不使用半精度--半精度只支持CUDA
		self.half = self.device.type != 'cpu'  # # FP16 supported on limited backends with CUDA

		# Load model 加载模型
		self.model = DetectMultiBackend(weights, self.device, dnn=False)
		self.stride = self.model.stride
		self.names = self.model.names
		self.pt = self.model.pt
		self.imgsz = check_img_size(imgsz, s=self.stride)

		# 不使用半精度
		if self.half:
			self.model.half()  # switch to FP16

		# read names and colors
		# names是类别名称字典；colors是画框时用到的颜色
		self.names = self.model.module.names if hasattr(self.model, 'module') else self.model.names
		self.colors = [[random.randint(0, 255) for _ in range(3)] for _ in self.names]

	# 当自动拍照时会调用这个函数
	def detect(self, source):
		# 输入 detect([img])
		if type(source) != list:
			raise TypeError('source must a list and contain picture read by cv2')

		# DataLoader 加载数据
		# 直接从 source 加载数据
		dataset = MyLoadImages(source)
		# 源程序通过路径加载数据，现在 source 就是加载好的数据，因此 LoadImages 就要重写
		bs = 1  # set batch size

		# 保存的路径
		vid_path, vid_writer = [None] * bs, [None] * bs

		# Run inference
		result = []
		if self.device.type != 'cpu':
			self.model(torch.zeros(1, 3, self.imgsz, self.imgsz).to(self.device).type_as(
				next(self.model.parameters())))  # run once
		dt, seen = (Profile(), Profile(), Profile()), 0

		for im, im0s in dataset:
			with dt[0]:
				im = torch.from_numpy(im).to(self.model.device)
				im = im.half() if self.model.fp16 else im.float()  # uint8 to fp16/32
				im /= 255  # 0 - 255 to 0.0 - 1.0
				if len(im.shape) == 3:
					im = im[None]  # expand for batch dim

				# Inference
				pred = self.model(im, augment=self.opt.augment)[0]

				# NMS
				with dt[2]:
					# max_det=2 最多检测两个目标，如果图片中有3个目标，需要修改
					pred = non_max_suppression(pred, self.opt.conf_thres, self.opt.iou_thres, self.opt.classes,
					                           self.opt.agnostic_nms, max_det=2)

				# Process predictions
				# 处理每一张图片
				# 原来的情况是要保持图片，因此多了很多关于保存路径上的处理。
				# 另外，pred其实是个列表。元素个数为batch_size
				det = pred[0]  # API 一次只处理一张图片，因此不需要 for 循环
				# copy 一个原图片的副本图片，不拷贝会对原图片造成影响
				im0 = im0s.copy()
				# 一张图片可能会有多个检测到的目标，标签也会有多个
				# result_txt = []  # 储存检测结果，每新检测出一个物品，长度就加一。
				#                  # 每一个元素是列表形式，储存着 类别，坐标，置信度
				xyxy_list = []
				conf_list = []
				class_id_list = []
				# 设置图片上绘制框的粗细，类别名称
				annotator = Annotator(im0, line_width=3, example=str(self.names))
				if len(det):
					# Rescale boxes from img_size to im0 size
					# 映射预测信息到原图
					det[:, :4] = scale_boxes(im.shape[2:], det[:, :4], im0.shape).round()

					#
					for *xyxy, conf, cls in reversed(det):
						# 只输出dog的信息,不用了就删除这个if语句
						# if self.names[int(cls)] == "dog":
						class_id = int(cls)
						xyxy_list.append(xyxy)
						conf_list.append(conf)
						class_id_list.append(class_id)

						line = (int(cls.item()), [int(_.item()) for _ in xyxy], conf.item())  # label format
						# result_txt.append(line)
						label = f'{self.names[int(cls)]} {conf:.2f}'
						# 跳入Annotator函数中，打印目标坐标和机械臂坐标
						x0, y0 = annotator.box_label(xyxy, label, color=self.colors[int(cls)])

			return im0, class_id_list, xyxy_list, conf_list

