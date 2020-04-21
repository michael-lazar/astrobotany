# ASCII (7-bit) printable characters

line = []
for i in range(32, 127):
    line.append(chr(i))
    if len(line) == 16:
        print("".join(line))
        line = []
print("".join(line))
