import os

def exists(filepath):
	found = False
	try:
		if os.stat(filepath)[6] > 0:
			found = True
	except:
		pass
	return found