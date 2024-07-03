import numpy as np
import random
import importlib.util
import os
import bloomfilter as bf
from sklearn import linear_model
import argparse
import time
from progress.bar import Bar
from tabulate import tabulate

# Enlace con la ruta para las utilidades (funciones de uso comun)
file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..',  'utils', 'utils.py'))
module_name = 'utils'

spec = importlib.util.spec_from_file_location(module_name, file_path)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)

class Rappor:
    def __init__(self,k,m,f,p,q,dataset,domain):
        self.k = m # Número de bits por Bloom Filter (Concordancia en la notación con el pseudocódigo)
        self.f = f
        self.p = p
        self.q = q
        self.dataset = dataset
        self.domain = domain
        self.B = bf.BloomFilter(m,k)

    def cliente(self,value):
        B = self.B.get_bloomfilter(value)
        B_prima = [self.perturbar_bit_PL(bit,self.f) for bit in B]
        S =  [self.perturbar_bit_TL(bit,self.p,self.q) for bit in B_prima]
        return S
    
    def perturbar_bit_PL(self,bit,f):
        return random.choice([0,1]) if(random.random() < f) else bit
    
    def perturbar_bit_TL(self,bit,p,q):
        if bit == 1:
            return 1 if random.random() < q else 0
        else:
            return 1 if random.random() < p else 0
    
    def execute(self):
        bar = Bar('Procesando datos de los clientes', max=len(self.dataset), suffix='%(percent)d%%')
        Informes = []
        t_cliente = 0
        for d in self.dataset:
            inicio = time.time()
            Informes.append(self.cliente(d))
            fin = time.time()
            t_cliente += (fin - inicio) * 1000
            bar.next()
        bar.finish()
        t_cliente = t_cliente/len(self.dataset)

        t_server = 0
        print('\n' + 'Ejecutando algortimo del servidor' + '\n')
        inicio = time.time()
        X = self.crear_matriz_diseno()
        contadores_estimados = self.estimar_contadores(Informes)
        Y = np.mat(contadores_estimados).T
        estimacion = self.regresion_lasso(X,Y)
        fin = time.time()
        t_server = (fin - inicio) * 1000

        F_estimada = {}
        j = 0
        for i in self.domain:
            F_estimada[i] = estimacion[j]
            j += 1
        
        # Tabla de tiempos de ejecución
        tiempos = [['Cliente (Por usuario)', str("{:.4f}".format(t_cliente)) + ' ms'],['Servidor (Estimar frecuencias)',str("{:.4f}".format(t_server)) + ' ms']]
        tabla_tiempos = tabulate(tiempos, headers=["Algoritmo", "Tiempo de Ejecución"], tablefmt="pretty")

        return F_estimada, tabla_tiempos

    def crear_matriz_diseno(self):
        M = []
        for cadena in self.domain:
            M.append(self.B.get_bloomfilter(cadena))

        return np.mat(M).T
    
    def estimar_contadores(self,Informes):
        N = len(Informes)
        Informes = np.mat(Informes)
        contadores = np.array(np.sum(Informes,0))[0]
        contadores_estimados = [(c - (0.5*f*q + p-0.5*f*q)*N)/((1-f)*(q-p)) for c in contadores]
        return contadores_estimados
    
    def regresion_lasso(self, X,Y):
        reg = linear_model.Lasso(alpha=0.1, positive=True)
        reg.fit(np.asarray(X),np.asarray(Y))
        return reg.coef_



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Algoritmo Sequence Fragment Puzzle para la estimación de frecuencias a partir de un diccionario desconocido.")
    # Parametros dependientes del caso de uso
    m = 64
    parser.add_argument("-m", type=int, required=True, help="m (Numero de bits de los filtros de bloom a emplear).")
    k = 6
    parser.add_argument("-k", type=int, required=True, help="k (Número de funciones hash empleadas).")
    f = 0.5
    parser.add_argument("-f", type=float, required=True, help="f (Probabilidad de perturbación permatente [0-1]).")
    p = 0.5
    parser.add_argument("-p", type=float, required=True, help="p (Probabilidad de perturbación temporal para bits 0 [0-1]).")
    parser.add_argument("-q", type=float, required=True, help="q (Probabilidad de perturbación temporal para bits 1 [0-1]).")
    q = 0.75
    parser.add_argument("-N", type=int, required=True, help='Numero de elementos del dataset generado.')
    parser.add_argument("-G", type=str, required=True, help='Tipo de generador [exp (exponencial), norm (normal), small (valores distribuidos en un dominio reducido)]')
    parser.add_argument("--verbose_time", action="store_true", help="Se desea obtener los tiempos de ejecución de las funciones.")
    args = parser.parse_args()
    # Generamos un flujo artificial de N datos 
    
    dataset,df, domain = utils.create_dataset(args.N,'exp')

    R = Rappor(args.k,args.m,args.f,args.p,args.q,dataset,domain)
    f_estimada, tiempos = R.execute()

    if(args.verbose_time): print(tiempos + '\n')
    utils.mostrar_resultados(df,f_estimada)


    


