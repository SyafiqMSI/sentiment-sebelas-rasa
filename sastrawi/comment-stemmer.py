# import StemmerFactory class
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

import json

data_path = 'backup/instagram_tagged_posts_20241229_195451.json'

# Open and read the JSON file
with open(data_path, 'r', encoding='utf-8') as file:
    data = json.load(file)

# create stemmer
factory = StemmerFactory()
stemmer = factory.create_stemmer()

# print(data[4]['comments'][0]['comment'])

for i in range(len(data[4]['comments'])) :
    output   = stemmer.stem(data[4]['comments'][i]['comment'])
    print(output)