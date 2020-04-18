import os
import sys

directory = sys.argv[1]

for filename in sorted(os.listdir(directory)):
    print(filename)
    print(open(os.path.join(directory, filename)).read())
