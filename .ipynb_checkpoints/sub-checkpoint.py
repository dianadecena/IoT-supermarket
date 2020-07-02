import ssl
import sys
import psycopg2
import paho.mqtt.client
import paho.mqtt.publish
import json
import time 
from datetime import datetime

class suscriptor:

    def __init__(self, my_connection):
        #se crea el cliente 
        self.client = paho.mqtt.client.Client()
        self.my_connection = my_connection
        self.no_alarma = 0

    def on_connect(self, client, userdata, flags, rc):    
        print('connected (%s)' % client._client_id)
        #se suscribe al canal por donde los dispositivos reportan los valores de los contaminantes cada hora 
        client.subscribe(topic='sucursal1/estantes/#', qos = 2) 
        client.subscribe(topic='sucursal2/estantes/#', qos = 2) 
        client.subscribe(topic='sucursal1/sensores', qos = 2) 
        client.subscribe(topic='sucursal2/sensores', qos = 2) 

    def on_data_estante(self, client, userdata, message):  
        a = json.loads(message.payload)
        #imprimir los datos y guardar datos en la bd    
        print(a)  
        print('---------------------------------------------------------')
        self.guardar_datos(a)
        if self.check_estante(a) == True:
            self.enviar_alarma_estante(a)
        
    def on_data_sensor(self, client, userdata, message):  
        a = json.loads(message.payload)
        #imprimir los datos y guardar datos en la bd    
        print(a)  
        print('---------------------------------------------------------')
        cur = self.my_connection.cursor()
        cur.execute("SELECT id_cliente FROM cliente_charcuteria WHERE id_sucursal = %s ORDER BY no_fila ASC LIMIT 2", (a["id_sucursal"],))
        self.my_connection.commit()
        ids = cur.fetchall()
        cur.close()
        if a["id_cliente"] in ids:
            self.enviar_alarma_sensor(a["sucursal"], a["id_cliente"])
            
    def check_estante(self, a):
        cur = self.my_connection.cursor()
        cur.execute("SELECT verificar_cantidad(%s)", (a["id_estante"],))
        self.my_connection.commit()
        activar = cur.fetchone()[0]
        cur.close()
        return activar 
    
    def conectar_suscriptor(self):
        host = "broker.hivemq.com"
        self.client.on_connect = self.on_connect
        self.client.message_callback_add('sucursal1/estantes/#', self.on_data_estante)
        self.client.message_callback_add('sucursal2/estantes/#', self.on_data_estante)
        self.client.message_callback_add('sucursal1/sensores', self.on_data_sensor)
        self.client.message_callback_add('sucursal2/sensores', self.on_data_sensor)
        self.client.connect(host=host) 
        self.client.loop_forever()

    def guardar_datos(self, a):
        #se guardan los datos en la base de datos 
        cur = self.my_connection.cursor()
        cur.execute("SELECT update_estante(%s, %s, %s)", (a["id_producto"], a["cantidad"], a["hora"]))
        self.my_connection.commit()
        print('datos guardados')
        
    def enviar_alarma_estante(self, a):
        #guardar alarma en la bd
        self.no_alarma += 1
        cur = self.my_connection.cursor()
        cur.execute("INSERT INTO activacion_alarma(no_alarma, id_estante, fecha_hora, activada) VALUES (%s, %s, %s, %s)", (self.no_alarma, a["id_estante"], a["hora"], True))
        self.my_connection.commit()
        cur.close()
        payload = {
                "activar": 'true',
                "id_estante": a["id_estante"]
        }
        print(payload)
        self.client.qos = 1
        self.client.publish(a["sucursal"]+'/alarmas/'+str(a["id_estante"]),json.dumps(payload),qos=1)
        
    def enviar_alarma_sensor(self, sucursal, id_cliente):
        payload = {
                "activar": 'true',
                "id_cliente": id_cliente
        }
        print(payload)
        self.client.qos = 1
        self.client.publish(sucursal+'alarmas/sensores',json.dumps(payload),qos=1)


