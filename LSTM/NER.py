import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras import preprocessing
from sklearn.model_selection import train_test_split
import numpy as np

# 학습 파일 불러오기
def read_file(file_name):
    sents = []
    with open(file_name, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for idx, l in enumerate(lines):
            if l[0] == ';' and lines[idx+1][0] == '$':
                this_sent=[]
            elif l[0] == '$' and lines[idx-1][0] == ';':
                continue
            elif l[0] == '\n':
                sents.append(this_sent)
            else:
                this_sent.append(tuple(l.split()))
    return sents

corpus = read_file('C:/Users/obybk/OneDrive/바탕 화면/인공지능/deepChat/LSTM/train.txt')
sentences, tags = [], []
for t in corpus:
    tagged_sentence = []
    sentence, bio_tag = [], []
    for w in t:
        tagged_sentence.append((w[1], w[3]))
        sentence.append(w[1])
        bio_tag.append(w[3])
    sentences.append(sentence)
    tags.append(bio_tag)
print("샘플 크기: \n", len(sentences))
print("0번째 샘플 문장 시퀀스: \n", sentences[0])
print("샘플 문장 시퀀스 최대 길이: ", max(len(l) for l in sentences))
print("샘플 문장 시퀀스 평균 길이: ", (sum(map(len, sentences))/len(sentences)))

#토크나이저 정의
sent_tokenizer = preprocessing.text.Tokenizer(oov_token='OOV') # 첫 인덱스는 OOV사용
sent_tokenizer.fit_on_texts(sentences)
tag_tokenizer = preprocessing.text.Tokenizer(lower=False)
tag_tokenizer.fit_on_texts(tags)

# 단어 사전 및 태그사전 크기
vocab_size = len(sent_tokenizer.word_index)+1
tag_size = len(tag_tokenizer.word_index)+1
print("BIO 태그 사전 크기 :", tag_size)
print("단어 사전 크기: ", vocab_size)

#학습용 단어 시퀀스 생성
x_train = sent_tokenizer.texts_to_sequences(sentences)
y_train = tag_tokenizer.texts_to_sequences(tags)
print(x_train[0])
print(y_train[0])

index_to_word = sent_tokenizer.index_word
index_to_ner = tag_tokenizer.index_word
index_to_ner[0] = 'PAD'

max_len = 40
x_train = preprocessing.sequence.pad_sequences(x_train, padding='post', maxlen=max_len)
y_train = preprocessing.sequence.pad_sequences(y_train, padding='post', maxlen=max_len)

x_train, x_test, y_train, y_test = train_test_split(x_train, y_train, test_size=.2, random_state = 0)

#출력데이터 원-핫 인코딩
y_train = tf.keras.utils.to_categorical(y_train, num_classes=tag_size)
y_test = tf.keras.utils.to_categorical(y_test, num_classes=tag_size)

print("학습 샘플 시퀀스 현상: ", x_train.shape)
print("학습 샘플 레이블 현상: ", y_train.shape)
print("테스트 샘플 시퀀스 형상: ", x_test.shape)
print("테스트 샘플 레이블 형상: ", y_test.shape)

# 모델 정의(Bi-LSTM)
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Embedding, Dense, TimeDistributed, Dropout, Bidirectional
from tensorflow.keras.optimizers import Adam

model = Sequential()
model.add(Embedding(input_dim=vocab_size, output_dim=30, input_length=max_len, mask_zero=True))
model.add(Bidirectional(LSTM(200, return_sequences=True, dropout=0.50, recurrent_dropout=0.25)))
model.add(TimeDistributed(Dense(tag_size, activation='softmax')))
model.compile(loss='categorical_crossentropy', optimizer=Adam(0.01), metrics=['accuracy'])
model.fit(x_train, y_train, batch_size=128, epochs=10)

print("평가 결과: ", model.evaluate(x_test, y_test)[1])

#시퀀스를 NER로 변환
def sequences_to_tag(sequences):
    result= []
    for sequences in sequences:
        temp = []
        for pred in sequences:
            pred_index = np.argmax(pred)
            temp.append(index_to_ner[pred_index].replace("PAD", "O"))
        result.append(temp)
    return result

# 테스트 데이터셋의 NER 예측
y_predicted = model.predict(x_test)
pred_tags = sequences_to_tag(y_predicted)
test_tags = sequences_to_tag(y_test)

# F1스코어 계산을 위해 사용
from seqeval.metrics import f1_score, classification_report
print(classification_report(test_tags, pred_tags))
print("F1-score: {:.1%}".format(f1_score(test_tags, pred_tags)))

#새로운 유형의 문장 NER 예측
word_to_index = sent_tokenizer.word_index
new_sentence = '삼성전자 출시 스마트폰 오늘 애플 도전장 내밀다.'.split()
new_x = []
for w in new_sentence:
    try:
        new_x.append(word_to_index.get(w,1))
    except KeyError:
        new_x.append(word_to_index['OOV'])

print('새로운 유형의 시퀀스: ', new_x)
new_padded_seqs = preprocessing.sequence.pad_sequences([new_x], padding="post", value=0, maxlen = max_len)
#NER예측

p = model.predict(np.array([new_padded_seqs[0]]))
p = np.argmax(p, axis= -1)
print("{:10}{:5}".format("단어", "예측된 NER"))
print("-"*50)
for w, pred in zip(new_sentence, p[0]):
    print("{:10}{:5}".format(w, index_to_ner[pred]))