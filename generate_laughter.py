from utils import q_to_one_hot, sample, onehot_to_wave, load_audio, mu_quantize
from keras.preprocessing.sequence import pad_sequences
import numpy as np
from wavenet import build_model
import pickle
from scipy.io import wavfile

'''
log 하고 weight 파일 이름 바꿔서 log_and_weight 에 옮겨주고
그리고 나서 아래 파라미터 이름 정해주고 돌릴 것.
'''
sr = 16000
sec = 3
sample_len = 16000
input_dim = 256
new_wave_name = './generation/laughter_my_voice'
audio_file = 'my_laughter'
seed_audio_path = '../laughter_audio_vector/' + audio_file + '.npy'
weight_path = './laughter_wavenet_weight.hdf5'
dilation_factor = [1,2,4,8,16,32,64,128,256,512,
                   1,2,4,8,16,32,64,128,256,512,
                   1,2,4,8,16,32,64,128,256,512]
impulse = {0: './impulse/impulse.wav'}

generated_sample = np.load(seed_audio_path)
generated_sample = generated_sample.tolist()
generated_sample = q_to_one_hot(generated_sample, input_dim).astype(np.uint8)
generated_sample = generated_sample[generated_sample.shape[0]-sample_len:generated_sample.shape[0]]
# sample_list = []
# sample_list.append(generated_sample)
# sample_list = pad_sequences(sample_list, maxlen=sample_len, padding='post')
# generated_sample = sample_list[0]
generated_sample = np.reshape(generated_sample, (1, sample_len, input_dim))
pred_seed = np.reshape(generated_sample, (-1, input_dim))

model = build_model(sample_len, dilation_factor)
model.load_weights(weight_path)

generation_step = sr * sec
prev_sample = -1
equal_cnt = 0
impulse_idx = 0

for i in range(generation_step):
    preds = model.predict(np.expand_dims(pred_seed, 0))  # prediction with the model
    sampled = sample(preds[0][-1])  # multinomial sampling
    # To prevent dead silence.
    if sampled == prev_sample:
        equal_cnt += 1
    else:
        equal_cnt = 0
    prev_sample = sampled
    sampled_onehot = np.zeros([1, 1, input_dim])
    sampled_onehot[0][0][sampled] = 1  # make the sample into onehot
    generated_sample = np.append(generated_sample, sampled_onehot, axis=1)  # append generated sample
    pred_seed = generated_sample[0][i + 1:i + 1 + sample_len]  # make new seed as generation input
    if equal_cnt > 1000:
        impulse_audio = load_audio(impulse[impulse_idx])
        impulse_audio = mu_quantize(impulse_audio, input_dim)
        impulse_audio = impulse_audio[:1000]
        impulse_audio = q_to_one_hot(impulse_audio, input_dim)
        for j in range(1000):
            pred_seed[sample_len - 1000 + j] = impulse_audio[j]
        print('Inject impulse.')
        if impulse_idx == len(impulse) - 1:
            impulse_idx = 0
        else:
            impulse_idx += 1
        equal_cnt = 0

    print('generated %ith sample ==> %i (equal_cnt = %i)' % ((i + 1), sampled, equal_cnt), end='\r')

# Save generated samples as a flie
with open(new_wave_name+'.pkl', 'wb') as f:
    pickle.dump(generated_sample, f)

# Make an audio file from generated results, generated_{sample_len}_{acc}.wav
quantized = onehot_to_wave(generated_sample, input_dim)
quantized = np.asarray(quantized)
wavfile.write(new_wave_name+'.wav', sr, quantized)

