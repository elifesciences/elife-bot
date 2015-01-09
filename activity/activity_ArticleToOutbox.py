import boto.swf
import json
import random
import datetime
import calendar
import time
import os

import activity

import boto.s3
from boto.s3.connection import S3Connection

import provider.filesystem as fslib

"""
ArticleToOutbox activity
"""

class activity_ArticleToOutbox(activity.activity):
	
	def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
		activity.activity.__init__(self, settings, logger, conn, token, activity_task)

		self.name = "ArticleToOutbox"
		self.version = "1"
		self.default_task_heartbeat_timeout = 30
		self.default_task_schedule_to_close_timeout = 60*5
		self.default_task_schedule_to_start_timeout = 30
		self.default_task_start_to_close_timeout= 60*5
		self.description = "Download a S3 object from the elife-articles bucket, unzip if necessary, and save to outbox folder on S3."
		
		# Create the filesystem provider
		self.fs = fslib.Filesystem(self.get_tmp_dir())
		
		# Bucket for outgoing files
		self.publish_bucket = settings.poa_packaging_bucket
		
		# Folder for pubmed XML
		self.pubmed_outbox_folder = "pubmed/outbox/"

	def do_activity(self, data = None):
		"""
		Do the work
		"""
		if(self.logger):
			self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
		
		elife_id = data["data"]["elife_id"]
		
		# Do not continue if it is a resupplied article
		if self.is_resupply(elife_id) is True:
			if(self.logger):
				self.logger.info('ArticleToOutbox: %s is a resupplied article' % elife_id)
			return True
		
		# Download the S3 object
		document = data["data"]["document"]
		self.fs.write_document_to_tmp_dir(document)
		
		# The document location on local file system
		tmp_document_path = self.get_document()
		# Clean up to get the filename alone
		tmp_document = self.get_document_name_from_path(tmp_document_path)
		
		# Get an S3 key name for where to save the XML
		delimiter = self.settings.delimiter
		prefix = self.pubmed_outbox_folder
		s3key_name = prefix + tmp_document
		
		# Create S3 key and save the file there
		bucket_name = self.publish_bucket
		
		s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
		bucket = s3_conn.lookup(bucket_name)
		
		s3key = boto.s3.key.Key(bucket)
		s3key.key = s3key_name
		s3key.set_contents_from_filename(tmp_document_path, replace=True)
		
		if(self.logger):
			self.logger.info('ArticleToOutbox: %s' % elife_id)

		return True
	
	def get_document(self):
		"""
		Exposed for running tests
		"""
		if(self.fs.tmp_dir):
			full_filename = self.fs.tmp_dir + os.sep + self.fs.get_document()
		else:
			full_filename = self.fs.get_document()
		
		return full_filename

	def get_document_name_from_path(self, document_path):
		"""
		Given a document location in the tmp directory
		slice away everything but the filename and return it
		"""
		document = document_path.replace(self.get_tmp_dir(), '')
		document = document.replace("", '')
		document = document.replace("\\", '')
		return document

	def is_resupply(self, doi_id):
		"""
		For overwriting XML file during the resupply, if there is a match
		with the DOI ids then do copy to the outbox
		"""
		
		volume_1_list = [3, 5, 7, 11, 13, 31, 47, 48, 49, 51, 65, 67, 68, 70, 78,
								 90, 93, 102, 109, 117, 171, 173, 181, 184, 205, 240, 242,
								 243, 248, 270, 281, 286, 301, 302, 311, 326, 340, 347,
								 351, 352, 353, 365, 385, 386, 387, 475]
		
		volume_2_list = [12, 36, 105, 116, 133, 160, 170, 178, 183, 190, 218, 220,
						 230, 231, 247, 260, 269, 278, 288, 290, 291, 299, 306, 308,
						 312, 321, 324, 327, 329, 333, 334, 336, 337, 348, 354, 358,
						 362, 367, 378, 380, 400, 411, 415, 421, 422, 425, 426, 429,
						 435, 444, 450, 452, 458, 459, 461, 467, 471, 473, 476, 477,
						 481, 482, 488, 491, 498, 499, 505, 508, 515, 518, 522, 523,
						 533, 534, 537, 542, 558, 563, 565, 569, 571, 572, 573, 577,
						 592, 593, 594, 603, 605, 615, 625, 626, 631, 632, 633, 638,
						 639, 640, 641, 642, 646, 647, 648, 654, 655, 658, 659, 663,
						 666, 668, 669, 672, 675, 676, 683, 691, 692, 699, 704, 708,
						 710, 712, 723, 726, 729, 731, 736, 744, 745, 747, 750, 757,
						 759, 762, 767, 768, 772, 776, 778, 780, 782, 785, 790, 791,
						 792, 799, 800, 801, 802, 804, 806, 808, 813, 822, 824, 825,
						 828, 842, 844, 845, 855, 856, 857, 861, 862, 863, 866, 868,
						 873, 882, 884, 886, 895, 899, 903, 905, 914, 924, 926, 932,
						 933, 940, 943, 947, 948, 951, 953, 954, 958, 960, 961, 963,
						 966, 967, 969, 971, 983, 992, 994, 996, 999, 1004, 1008, 1009,
						 1020, 1029, 1030, 1042, 1045, 1061, 1064, 1067, 1071, 1074,
						 1084, 1085, 1086, 1089, 1096, 1098, 1102, 1104, 1108, 1114,
						 1115, 1119, 1120, 1123, 1127, 1133, 1135, 1136, 1138, 1139,
						 1140, 1149, 1157, 1159, 1160, 1169, 1179, 1180, 1197, 1202,
						 1206, 1211, 1213, 1214, 1221, 1222, 1228, 1229, 1233, 1234,
						 1236, 1252, 1256, 1270, 1273, 1279, 1287, 1289, 1291, 1293,
						 1294, 1295, 1296, 1298, 1299, 1305, 1312, 1319, 1323, 1326,
						 1328, 1339, 1340, 1341, 1345, 1350, 1387, 1388, 1402, 1403,
						 1414, 1426, 1428, 1456, 1462, 1469, 1482, 1494, 1501, 1503,
						 1514, 1515, 1516, 1519, 1541, 1557, 1561, 1574, 1587, 1597,
						 1599, 1605, 1608, 1633, 1658, 1662, 1663, 1680, 1700, 1710,
						 1738, 1749, 1760, 1779, 1809, 1816, 1820, 1839, 1845, 1873,
						 1893, 1926, 1968, 1979, 2094]
		
		volume_3_list = [590, 829, 1201, 1239, 1257, 1267, 1308, 1310, 1311, 1322, 1355, 1369, 
						1370, 1374, 1381, 1385, 1386, 1412, 1433, 1434, 1438, 1439, 1440, 1457, 
						1460, 1465, 1473, 1479, 1481, 1483, 1488, 1489, 1496, 1498, 1524, 1530, 
						1535, 1539, 1566, 1567, 1569, 1579, 1581, 1584, 1596, 1603, 1604, 1607, 
						1610, 1612, 1621, 1623, 1630, 1632, 1637, 1641, 1659, 1671, 1681, 1684, 
						1694, 1695, 1699, 1715, 1724, 1730, 1739, 1741, 1751, 1754, 1763, 1775, 
						1776, 1808, 1812, 1817, 1828, 1831, 1832, 1833, 1834, 1846, 1849, 1856, 
						1857, 1861, 1867, 1879, 1883, 1888, 1892, 1901, 1906, 1911, 1913, 1914, 
						1916, 1917, 1928, 1936, 1939, 1944, 1948, 1949, 1958, 1963, 1964, 1967, 
						1977, 1982, 1990, 1993, 1998, 2001, 2008, 2009, 2020, 2024, 2025, 2028, 
						2030, 2040, 2041, 2042, 2043, 2046, 2053, 2057, 2061, 2062, 2069, 2076, 
						2077, 2078, 2087, 2088, 2104, 2105, 2109, 2112, 2115, 2130, 2131, 2137, 
						2148, 2151, 2152, 2164, 2171, 2172, 2181, 2184, 2189, 2190, 2196, 2199, 
						2200, 2203, 2206, 2208, 2217, 2218, 2224, 2230, 2236, 2238, 2242, 2245, 
						2252, 2257, 2260, 2265, 2270, 2272, 2273, 2277, 2283, 2286, 2289, 2304, 
						2313, 2322, 2324, 2349, 2362, 2365, 2369, 2370, 2372, 2375, 2384, 2386, 
						2387, 2391, 2394, 2395, 2397, 2403, 2407, 2409, 2419, 2439, 2440, 2443, 
						2444, 2445, 2450, 2451, 2475, 2478, 2481, 2482, 2490, 2501, 2504, 2510, 
						2511, 2515, 2516, 2517, 2523, 2525, 2531, 2535, 2536, 2555, 2557, 2559, 
						2564, 2565, 2576, 2583, 2589, 2590, 2598, 2615, 2618, 2619, 2626, 2630, 
						2634, 2637, 2641, 2653, 2658, 2663, 2667, 2669, 2670, 2671, 2674, 2676, 
						2678, 2687, 2715, 2725, 2726, 2730, 2734, 2736, 2740, 2743, 2747, 2750, 
						2755, 2758, 2763, 2772, 2780, 2784, 2786, 2791, 2792, 2798, 2805, 2809, 
						2811, 2812, 2813, 2833, 2839, 2840, 2844, 2848, 2851, 2854, 2860, 2862, 
						2863, 2866, 2872, 2875, 2882, 2893, 2897, 2904, 2907, 2910, 2917, 2935, 
						2938, 2945, 2949, 2950, 2951, 2956, 2963, 2964, 2975, 2978, 2981, 2993, 
						2996, 2999, 3005, 3007, 3011, 3023, 3025, 3031, 3032, 3035, 3043, 3058, 
						3061, 3068, 3069, 3075, 3077, 3080, 3083, 3091, 3100, 3104, 3110, 3115, 
						3116, 3125, 3126, 3128, 3145, 3146, 3159, 3164, 3176, 3178, 3180, 3185, 
						3191, 3197, 3198, 3205, 3206, 3222, 3229, 3233, 3235, 3239, 3245, 3251, 
						3254, 3255, 3271, 3273, 3275, 3285, 3293, 3297, 3300, 3307, 3311, 3318, 
						3342, 3346, 3348, 3351, 3357, 3363, 3371, 3372, 3374, 3375, 3383, 3385, 
						3397, 3399, 3401, 3405, 3406, 3421, 3422, 3427, 3430, 3433, 3435, 3440, 
						3443, 3464, 3467, 3468, 3473, 3475, 3476, 3496, 3497, 3498, 3502, 3504, 
						3521, 3523, 3526, 3528, 3532, 3545, 3549, 3553, 3558, 3563, 3564, 3568, 
						3573, 3574, 3575, 3579, 3581, 3583, 3587, 3596, 3600, 3602, 3604, 3606, 
						3609, 3613, 3626, 3635, 3638, 3640, 3641, 3648, 3650, 3653, 3656, 3658, 
						3663, 3665, 3671, 3674, 3676, 3678, 3679, 3680, 3683, 3695, 3696, 3701, 
						3702, 3703, 3706, 3711, 3714, 3720, 3722, 3724, 3726, 3727, 3728, 3735, 
						3737, 3743, 3754, 3756, 3764, 3765, 3766, 3772, 3779, 3781, 3785, 3790, 
						3804, 3811, 3821, 3830, 3842, 3848, 3851, 3881, 3883, 3891, 3892, 3895, 
						3896, 3908, 3915, 3939, 3941, 3943, 3949, 3962, 3970, 3978, 3980, 3981, 
						3997, 4006, 4008, 4014, 4034, 4037, 4040, 4046, 4057, 4059, 4066, 4070, 
						4094, 4106, 4111, 4123, 4126, 4132, 4135, 4137, 4147, 4165, 4168, 4177, 
						4180, 4187, 4193, 4205, 4207, 4220, 4234, 4235, 4236, 4246, 4247, 4249, 
						4265, 4266, 4273, 4279, 4287, 4288, 4300, 4333, 4353, 4366, 4371, 4380, 
						4387, 4390, 4395, 4402, 4406, 4418, 4433, 4449, 4476, 4478, 4491, 4499, 
						4501, 4530, 4543, 4551, 4553, 4563, 4565, 4577, 4580, 4600, 4601, 4603, 
						4629, 4630, 4631, 4664, 4686, 4692, 4741, 4742, 4766, 4779, 4811, 4869, 
						4875, 4878, 4901, 4902, 4909, 4969, 4997, 4998, 5000, 5031, 5041, 5060, 
						5075, 5087, 5115, 5179, 5218, 5244, 5256, 5259, 5377, 5394, 5418, 5419, 
						5427, 5490, 5504, 5570, 5580, 5614, 5657, 5720, 5816]
		
		if (   int(doi_id) in volume_1_list
			or int(doi_id) in volume_2_list
			or int(doi_id) in volume_3_list):
			return True
		else:
			return False