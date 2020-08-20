import tensorflow as tf

def build_model(n_vocab, d_model, n_output, n_seq):
    inputs = tf.keras.layers.Input(n_seq,)  # (bs, n_seq)

    embedding = tf.keras.layers.Embedding(n_vocab, d_model)
    hidden = embedding(inputs)  # (bs, n_seq, d_model)

    lstm1 = tf.keras.layers.Bidirectional(tf.keras.layers.LSTM(units=d_model // 2, return_sequences=True, return_state=True))
    hidden, fw_h, fw_c, bw_h, bw_c = lstm1(hidden)  # (bs, n_seq, d_model), (bs, d_model // 2) * 4

    lstm2 = tf.keras.layers.Bidirectional(tf.keras.layers.LSTM(units=d_model // 2, return_sequences=True))
    hidden = lstm2(hidden, initial_state=(fw_h, fw_c, bw_h, bw_c))  # (bs, n_seq, d_model)

    dense1 = tf.keras.layers.Dense(d_model, activation=tf.nn.relu)
    hidden = dense1(hidden)  # (bs, n_seq, d_model)

    dense2 = tf.keras.layers.Dense(n_output)
    outputs = dense2(hidden)  # (bs, n_seq, n_output)

    # crf = CRF()
    # outputs = crf(outputs)  # (bs, n_seq, n_output)

    outputs = tf.keras.layers.Softmax()(outputs)

    model = tf.keras.Model(inputs=inputs, outputs=outputs)
    return model