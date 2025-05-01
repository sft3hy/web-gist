import re

urls = []
rows = open("txt_files/Links.txt", "r").read().split("\n")
for row in rows:
    if row == "":
        urls.append("")
    else:
        urls.append(row)

print(len(urls))
print(urls[1183])
