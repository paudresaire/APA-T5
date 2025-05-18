import struct as st

'''
Pau Dresaire

En este fichero se definen 4 funciones relacionadas con la manipulación de ficheros .wav
a parte de dos funciones auxiliares para empaquetar y desempaquetar la cabecera.

Funciones para el manejo de señales estéreo en archivos WAVE:
- Conversión estéreo a mono y mono a estéreo
- Codificación y decodificación estéreo en 32 bits (semisuma y semidiferencia)
- Manipulación directa del subchunk 'data' de ficheros RIFF WAVE con PCM lineal
'''

''''
Trama WAVE:
- RIFF: chunkID (4B), chunkSize (4B), Format (4B)

- The 'fmt' sub-chunk: subchunk1ID (4B), subchunk1Size (4B), audioFormat (2B), numChannels (2B), sampleRate (4B), byteRate (4B), blockAlign (2B), bitsPerSample (2B)

- Data: subchunk2ID (4B), subchunk2Size (4B), data
'''

def desempaquetar_cabecera_wav(c):
	(chunkId, chunkSize, format,
     subchunk1Id, subchunk1Size, audioFormat,
     numChannels, sampleRate, byteRate,
     blockAlign, bitsPerSample,
     subchunk2Id, subchunk2Size) = st.unpack('<4sI4s4sIHHIIHH4sI', c)

	return {
		"chunkId": chunkId,
		"chunkSize": chunkSize,
		"format": format,
		"subchunk1Id": subchunk1Id,
		"subchunk1Size": subchunk1Size,
		"audioFormat": audioFormat,
		"numChannels": numChannels,
		"sampleRate": sampleRate,
		"byteRate": byteRate,
		"blockAlign": blockAlign,
		"bitsPerSample": bitsPerSample,
		"subchunk2Id": subchunk2Id,
		"subchunk2Size": subchunk2Size,
	}

def empaquetar_cabecera_wav(c):
	return st.pack('<4sI4s4sIHHIIHH4sI',
		c['chunkId'],
		c['chunkSize'],
		c['format'],
		c['subchunk1Id'],
		c['subchunk1Size'],
		c['audioFormat'],
		c['numChannels'],
		c['sampleRate'],
		c['byteRate'],
		c['blockAlign'],
		c['bitsPerSample'],
		c['subchunk2Id'],
		c['subchunk2Size']
	)

def estereo2mono(ficEste, ficMono, canal=2):
	with open(ficEste, 'rb') as fdEstereo:
		cabecera = fdEstereo.read(44)
	cabeceraDesempaquetada = desempaquetar_cabecera_wav(cabecera)

	# Comprovem que sigui estereo i 16 bits
	if cabeceraDesempaquetada['numChannels'] != 2 or cabeceraDesempaquetada['bitsPerSample'] != 16:
		print("El fitxer no és estèreo o no té mostres de 16 bits")
		return None
		
	# Llegim les dades saltant els primers 44 bytes
	with open(ficEste, 'rb') as fdDades:
		fdDades.seek(44)
		rawData = fdDades.read()
	samples = st.unpack('<' + 'h' * (len(rawData) // 2), rawData)

	L = samples[::2]
	R = samples[1::2]
	
	if canal == 0:
		mono = L
	elif canal == 1:
		mono = R
	elif canal == 2:
		mono = [(l + r) // 2 for l, r in zip(L, R)]
	elif canal == 3:
		mono = [(l - r) // 2 for l, r in zip(L, R)]
	else:
		raise ValueError("canal ha de ser 0, 1, 2 o 3")

	# Canviem les dades de la capçalera amb la nova versió
	monoData = st.pack('<' + 'h' * len(mono), *mono)
	cabeceraDesempaquetada['numChannels'] = 1
	cabeceraDesempaquetada['subchunk2Size'] = len(monoData)
	cabeceraDesempaquetada['chunkSize'] = 36 + cabeceraDesempaquetada['subchunk2Size']
	cabeceraDesempaquetada['byteRate'] = cabeceraDesempaquetada['sampleRate'] * cabeceraDesempaquetada['numChannels'] * cabeceraDesempaquetada['bitsPerSample'] // 8
	cabeceraDesempaquetada['blockAlign'] = cabeceraDesempaquetada['numChannels'] * cabeceraDesempaquetada['bitsPerSample'] // 8

	newHeader = empaquetar_cabecera_wav(cabeceraDesempaquetada)

	with open(ficMono, 'wb') as fdMono:
		fdMono.write(newHeader)
		fdMono.write(monoData)

# Suma
estereo2mono('wav/komm.wav', 'wav/sortida_mono.wav')
# Canal esquerre
estereo2mono('wav/komm.wav', 'wav/sortida_L.wav', canal=0)
# Canal dret
estereo2mono('wav/komm.wav', 'wav/sortida_R.wav', canal=1)
# Resta
estereo2mono('wav/komm.wav', 'wav/sortida_diferencia.wav', canal=3)


def mono2estereo(ficIzq, ficDer, ficEste):
	# Obrim els dos arxius a la vegada
	with open(ficIzq, 'rb') as fdIzq, open(ficDer, 'rb') as fdDer:
		headerIzq = fdIzq.read(44)
		headerDer = fdDer.read(44)

		cabeceraIzq = desempaquetar_cabecera_wav(headerIzq)
		cabeceraDer = desempaquetar_cabecera_wav(headerDer)

		if cabeceraIzq['numChannels'] != 1 or cabeceraDer['numChannels'] != 1:
			print("Error! Els fitxers han de ser mono")
			return
		if cabeceraIzq['bitsPerSample'] != 16 or cabeceraDer['bitsPerSample'] != 16:
			print("Error! Els fitxers han de ser de 16 bits")
			return
		
		# Mirem que tinguin les mateixes dimensions per juntarles
		if cabeceraIzq['sampleRate'] != cabeceraDer['sampleRate'] or cabeceraIzq['subchunk2Size'] != cabeceraDer['subchunk2Size']:
			print("Els fitxers d'entrada han de tenir la mateixa duració i freqüència")

		dataIzq = fdIzq.read()
		dataDer = fdDer.read()

		muestrasIzq = st.unpack('<' + 'h' * (len(dataIzq) // 2), dataIzq)
		muestrasDer = st.unpack('<' + 'h' * (len(dataDer) // 2), dataDer)

		# Intercalem les mostres
		combined = []
		for l, r in zip(muestrasIzq, muestrasDer):
			combined.append(l)
			combined.append(r)
		data = st.pack('<' + 'h' * len(combined), *combined)

		cabeceraEstereo = cabeceraIzq.copy()
		cabeceraEstereo['numChannels'] = 2
		cabeceraEstereo['byteRate'] = cabeceraEstereo['sampleRate'] * cabeceraEstereo['numChannels'] * cabeceraEstereo['bitsPerSample'] // 8
		cabeceraEstereo['blockAlign'] = cabeceraEstereo['numChannels'] * cabeceraEstereo['bitsPerSample'] // 8
		cabeceraEstereo['subchunk2Size'] = len(data)
		cabeceraEstereo['chunkSize'] = 36 + cabeceraEstereo['subchunk2Size']

		newHeader = empaquetar_cabecera_wav(cabeceraEstereo)

		with open(ficEste, 'wb') as fdEste:
			fdEste.write(newHeader)
			fdEste.write(data)

# Canal esquerre
mono2estereo('wav/sortida_L.wav', 'wav/sortida_R.wav', 'wav/reconstruccio_estereo.wav')

def codEstereo(ficEste, ficCod):
	with open(ficEste, 'rb') as fd:
		c = fd.read(44)
		cabecera = desempaquetar_cabecera_wav(c)

		if cabecera['numChannels'] != 2 or cabecera['bitsPerSample'] != 16:
			print('Error: el fitxer ha de fer estèreo amb mostres de 16 bits')
			return
		
		data = fd.read()
		mostres = st.unpack('<' + 'h' * (len(data) // 2), data)
		L = mostres[::2]
		R = mostres[1::2]

		# Agruparem cada parell L-R en una mostra de 32 bits
		muestras = []
		for l, r in zip(L, R):
			valor = (r & 0xFFFF) << 16 | (l & 0xFFFF)
			muestras.append(valor)

		cabecera['numChannels'] = 1
		cabecera['bitsPerSample'] = 32
		cabecera['byteRate'] = cabecera['sampleRate'] * 4
		cabecera['blockAlign'] = 4
		cabecera['subchunk2Size'] = len(muestras) * 4
		cabecera['chunkSize'] = 36 + cabecera['subchunk2Size']

		cabeceraNueva = empaquetar_cabecera_wav(cabecera)

		with open(ficCod, 'wb') as fdCod:
			fdCod.write(cabeceraNueva)
			fdCod.write(st.pack('<' + 'I' * len(muestras), *muestras))

codEstereo('wav/komm.wav', 'wav/komm_codificat_32b.wav')


def decEstereo(ficCod, ficEste):
	with open(ficCod, 'rb') as fd:
		c = fd.read(44)
		cabecera = desempaquetar_cabecera_wav(c)

		if cabecera['numChannels'] != 1 or cabecera['bitsPerSample'] != 32:
				print("Error: El fitxer d'entrada ha de ser mono amb mostres de 32 bits.")
				return
		
		data = fd.read()
		muestras = st.unpack('<' + 'I' * (len(data) // 4), data)

		semiSums = list(map(lambda x: st.unpack('<h', st.pack('<H', (x >> 16) & 0xFFFF))[0], muestras))
		semiDiffs = list(map(lambda x: st.unpack('<h', st.pack('<H', x & 0xFFFF))[0], muestras))

		L = [max(-32768, min(32767, s + d)) for s, d in zip(semiSums, semiDiffs)]
		R = [max(-32768, min(32767, s - d)) for s, d in zip(semiSums, semiDiffs)]

		cabecera['numChannels'] = 2
		cabecera['bitsPerSample'] = 16
		cabecera['byteRate'] = cabecera['sampleRate'] * 4
		cabecera['blockAlign'] = 4
		cabecera['subchunk2Size'] = len(L) * 4
		cabecera['chunkSize'] = 36 + cabecera['subchunk2Size']

		cabeceraNueva = empaquetar_cabecera_wav(cabecera)
		m = [val for pair in zip(L, R) for val in pair]

		with open(ficEste, 'wb') as fdEste:
				fdEste.write(cabeceraNueva)
				fdEste.write(st.pack('<' + 'h' * len(m), *m))


decEstereo('wav/komm_codificat_32b.wav', 'wav/komm_reconstruccio_16b.wav')