# -*- coding:utf-8 -*-

import logging
import numpy as np
import collections
import sentencepiece as spm
from .model import build_model

# net_tag list
NER_TAG = [
    "PAD",  # PAD.  other 태그와 구분시켜줄 태그
    "O",  # other
    "B_DAT",  # 날짜
    "I_DAT",
    "B_DUR",  # 기간
    "I_DUR",
    "B_LOC",  # 위치
    "I_LOC",
    "B_MNY",  # 통화
    "I_MNY",
    "B_NOH",  # 수량
    "I_NOH",
    "B_ORG",  # 기관
    "I_ORG",
    "B_PER",  # 사람
    "I_PER",
    "B_PNT",  # 비율
    "I_PNT",
    "B_POH",  # 기타
    "I_POH",
    "B_TIM",  # 시간
    "I_TIM",
]

# ner_tag dictionary
NER_TAG_DIC = {}
for entity in NER_TAG:
    NER_TAG_DIC[entity] = len(NER_TAG_DIC)

# ner_tag index
NER_TAG_IDX = {}
for key, value in NER_TAG_DIC.items():
    NER_TAG_IDX[value] = key
NER_TAG_IDX

# 로그
logger = logging.getLogger("chatbot")

# vocab
vocab = spm.SentencePieceProcessor()
vocab.Load("./ko_8000.model")  # 실행시키면 web_server.py가 실행되고 거기서 호출하는 것이므로, web_server.py 기준으로 경로를 적어줘야 함!

n_seq = 128
n_vocab = len(vocab)
d_model = 512
n_output = len(NER_TAG)

# model
model = build_model(n_vocab, d_model, n_output, n_seq)
model.summary()

# load trained weights
model.load_weights("entity/ner_rnn.hdf5")


# 입력에 대한 entity 조회
def get_entity(recv_value):
    output = do_predict(recv_value["input"])
    return output


# 모델로 추론은 piece 단위로 하고,
# 그걸 다시 띄어쓰기 단어 단위로 모아서 
# 상대적으로 많은 entity가 선택되거나 동률이면 앞에것으로 entity를 선택

def choice_entity(entities):
    # print(entities)
    dic = collections.OrderedDict()
    for entity in entities:
        if entity not in dic:
            dic[entity] = 0
        dic[entity] += 1
    print(dic)
    entity, count = "", 0
    for key, value in dic.items():
        # print(count, key, value)
        if count < value:
            entity = key
            count = value
    return entity


def do_predict(string):
    tokens = vocab.encode_as_pieces(string)
    inputs = vocab.encode_as_ids(string)
    inputs += [0] * (n_seq - len(inputs))
    inputs = inputs[:n_seq]

    outputs = model.predict(np.array([inputs]))
    tkn_idx = np.argmax(outputs[0], axis=1)[:len(tokens)]
    tkn_type = [NER_TAG_IDX[idx] for idx in tkn_idx]

    assert len(tkn_type) == len(tokens)
    print(tokens)
    print(tkn_type)
    tags, tag, entities = [], [], []
    for token, type in zip(tokens, tkn_type):
        # space를 미리 계산
        if token.startswith(u"\u2581"):
            space = True
            token = token[1:]
        else:
            space = False
        
        if space and tag:
            if entities:
                tags.append(["".join(tag).strip(), choice_entity(entities)])
            tag, entities = [], []
        tag.append(token)
        if type != "O":
            entities.append(type[2:])

    if tag and entities:
        tags.append(["".join(tag).strip(), choice_entity(entities)])

    print(len(tags))
    return tags