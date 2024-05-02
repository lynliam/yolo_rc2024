import cv2
from pyzbar.pyzbar import decode
import matlablib

cap = cv2.VideoCapture(0)

data = ['link', 'tile']

red = (0, 0, 255)
green = (0, 255, 0)

while True:
	success, img = cap.read()
	QR_Code = decode(img)

	for QR in QR_Code:
		QR_data = QR.data.decode('utf-8')

		if QR_data != data[-1] and QR_data != data[-2]:
			data.append(QR_data)
			print(data)

		point = QR.rect
		x0 = (int(point[2]))/2
		y0 = (int(point[3]))/2
		x = int(point[0])+int(x0)
		y = int(point[1])+int(y0)
		center_data = str((x, y))
		cv2.rectangle(img, (point[0], point[1]), (point[0] + point[2], point[1] + point[3]), green, 5)
		cv2.putText(img, QR_data, (point[0], point[1] - 10), cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.55, green, 1)
		cv2.circle(img, (x, y), 2, green, 1, -1)
		cv2.putText(img, center_data, (x, y), cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.55, green, 1)
		'''
		if QR_data == "baozi":
			cv2.rectangle(img, (point[0], point[1]), (point[0] + point[2], point[1] + point[3]), green, 5)
			cv2.putText(img, QR_data, (point[0], point[1] - 10), cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.55, green, 1)
			cv2.circle(img, (x, y), 2, green, 1, -1)
			cv2.putText(img, center_data, (x, y), cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.55, green, 1)
		else:
			cv2.rectangle(img, (point[0], point[1]), (point[0] + point[2], point[1] + point[3]), red, 5)
			cv2.putText(img, QR_data, (point[0], point[1] - 10), cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.55, red, 1)
			cv2.circle(img, (x, y), 2, red, 1, -1)
			cv2.putText(img, center_data, (x, y), cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.55, red, 1)
		'''
	cv2.imshow("output", img)

	if cv2.waitKey(1) & 0XFF == 27:
		break
