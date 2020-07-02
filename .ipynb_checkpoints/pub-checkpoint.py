import ssl
import sys
import time
import paho.mqtt.client
import paho.mqtt.publish
import json
import datetime 
import random 
import numpy as np

class publicador:
    
    def __init__(self, connection, nombre):
        #se crea el cliente 
        self.client = paho.mqtt.client.Client(nombre, False)
        self.connection = connection
        self.activar_alarma_estante = False
        self.alarma_activada = 0
        
    def conectar_dispositivo(self):
        #se conecta al host publico de HiveMQ usando qos=2 para hacer que 
        #la informacion llegue exactamente una vez y así evitar errores cuando se guarden en la base de datos
        host = "broker.hivemq.com"
        self.client.qos = 2
        self.client.connect(host=host)

    def enviar_mensaje(self, sucursal, producto, cantidad, id_estante, hora):
        payload = {
                "id_producto": producto,
                "cantidad": cantidad,
                "id_estante": id_estante,
                "sucursal": sucursal,
                "hora": str(hora)
            }
        print(payload)
        self.client.publish(sucursal+'/estantes/'+str(id_estante),json.dumps(payload),qos=2)
        time.sleep(0.5)
        
    def enviar_mensaje_sensor(self, sucursal, id_cliente, id_sucursal):
        payload = {
                "sucursal": sucursal,
                "id_cliente": id_cliente,
                "id_sucursal": id_sucursal
            }
        print(payload)
        self.client.publish(sucursal+'/sensores',json.dumps(payload),qos=2)
        time.sleep(0.5)

    def on_connect(self, client, userdata, flags, rc):    
        print('se ha suscrito correctamente (%s)' % client._client_id)
        #el dispositivo se suscribe al canal por donde se notificará que se debe activar la alarma 
        #de alguno o todos los dispositivos 
        self.client.subscribe(topic='sucursal1/alarmas/#',qos=1)
        self.client.subscribe(topic='sucursal2/alarmas/#',qos=1)

    def on_message(self, client, userdata, message):   
        a = json.loads(message.payload)
        print(a) 
        self.activar_alarma(a["id_estante"])
        if a["id_cliente"] != None:
            self.activar_alarma_sensor(a)
    
    def conectar_suscriptor(self):
        self.client = paho.mqtt.client.Client()
        host = "broker.hivemq.com"
        self.client.on_connect = self.on_connect
        self.client.message_callback_add('sucursal1/alarmas/#', self.on_message)  
        self.client.message_callback_add('sucursal2/alarmas/#', self.on_message)  
        self.client.connect(host=host) 
        self.client.loop_forever()
    
    def activar_alarma(self, id_estante):
        print('----------------------------------------------')
        print('    alarma activada estante: '+str(id_estante) )
        print('----------------------------------------------')
        self.activar_alarma_estante = True 
        
    def activar_alarma_sensor(self, a):
        self.alarma_activada = a["id_cliente"]
    
    def iniciar_sucursal(self):
        #se carga el json con la data de los clientes
        with open('Data/clientes.json') as f:
            clientes = json.load(f)

        #se inicializan los contadores  
        day = 0
        no_fila = 0
        cont_tiempo = 0
        cont_factura = 0
        no_visita = 0
        cont_horas = 0
        horas = 0

        #se establece la hora inicial en que empieza a funcionar
        hora = datetime.datetime.now().replace(minute=0, second=0) 

        #se elige una cantidad random de personas que van a entrar 
        cantidad = random.randint(1, 10)
        #aquí se guardan los indices de los clientes dentro de una sucursal (los que tienen en el json) para poder acceder a estos después
        indices = []

        #se eligen varios varios valores aleatorios según la cantidad de clientes que va a entrar 
        for i in range(cantidad):
            values = list(range(0, len(clientes)))
            for j in indices:
                values.remove(j)
            #se elige un valor random 
            r1 = random.choice(values)
            #se guardan los indices seleccionados 
            indices.append(r1)
            
        #se inicializa el contador de los clientes 
        for i in range(0, len(clientes)):
            clientes[i]["contador"] = 0
            clientes[i]["sucursal"] = 0

        while(day < 30): 
            #se ejecuta el proceso de compra para cada cliente cuyo indices en el json este en el array indices 
            for i in indices:
                #se actualiza el contador cuando entra por primera vez
                clientes[i]["contador"] += 1 
                #se cuenta cuando pase una vuelta completa del for
                if indices[len(indices)-1] == i:
                    cont_tiempo += 1
                    cont_horas += 1
                #actualizamos el estado de la persona 
                cliente_actual = json.dumps(clientes[i]["id_cliente"])
                print("Cliente id:", cliente_actual, " Indice: ", i)
                print("Indices: "+str(indices))
                #aumentar contador de visitas 
                no_visita += 1
                #si el contador del cliente es igual a 1 es porque entro por primera vez
                if clientes[i]["contador"] == 1:
                    #se elige de manera aleatoria la sucursal en la que está 
                    sucursal = random.randint(1, 2)
                    clientes[i]["sucursal"] = sucursal
                    #la cámara capta su rostro y verifica si pertenece al programa de fidelidad 
                    cur = self.connection.cursor()
                    cur.execute("SELECT verificar_pertenece_programa(%s)", (clientes[i]["id_cliente"],))
                    self.connection.commit()
                    pertenece = cur.fetchone()[0]
                    cur.close()
                    if pertenece == True:
                        #si pertenece se cuenta su visita 
                        hora = datetime.datetime.now().replace(minute=0, second=0) 
                        cur = self.connection.cursor()
                        cur.execute("INSERT INTO visita(no_visita, no_cuenta, id_cliente, id_sucursal, fecha_hora) VALUES (%s, (SELECT no_cuenta FROM cuenta_programa_fidelidad WHERE id_cliente = %s), %s, %s, %s)", (no_visita, clientes[i]["id_cliente"], clientes[i]["id_cliente"], sucursal, hora,))
                        self.connection.commit()
                        cur.close()
                    else:
                        #si no pertenece se cuenta la visita de un desconocido 
                        hora = datetime.datetime.now().replace(minute=0, second=0) 
                        cur = self.connection.cursor()
                        cur.execute("INSERT INTO visita(no_visita, no_cuenta, id_cliente, id_sucursal, fecha_hora) VALUES (%s, %s, %s, %s, %s)", (no_visita, 0, 0, sucursal, hora,))
                        self.connection.commit()
                        cur.close()
                    #se inicializa el carrito donde guardaran los productos 
                    clientes[i]["carrito"] = []
                    #se elige de manera aleatoria si irá a un pasillo o a buscar un ticket para que lo atiendan el la charcutería
                    opciones = list(["ir a un pasillo", "ir a la charcutería"])
                    decision = random.choice(opciones)
                    print("El cliente va a "+str(decision))
                    #se actualiza el estado del cliente
                    clientes[i]["currently"] = decision
                else: 
                    #si no es la primera vez que entra al supermercado se verifica si el cliente está en la cola para la charcutería 
                    sucursal = clientes[i]["sucursal"]
                    cur = self.connection.cursor()
                    cur.execute("SELECT verificar_cola(%s)", (clientes[i]["id_cliente"],))
                    self.connection.commit()
                    is_en_cola = cur.fetchone()[0]
                    cur.close()
                    if is_en_cola == True:
                        #si está en la cola se verifica si la alarma de su sensor se activó para que lo atiendan 
                        if self.alarma_activada == clientes[i]["id_cliente"]:
                            #va a ser atendido en la charcutería
                            #se borra de la fila el cliente
                            cur = self.connection.cursor()
                            cur.execute("DELETE FROM cliente_charcuteria WHERE id_cliente = %s", (clientes[i]["id_cliente"],))
                            self.connection.commit()
                            cur.close()
                            #actualizar fila 
                            cur = self.connection.cursor()
                            cur.execute("UPDATE cliente_charcuteria SET no_fila = cliente_charcuteria.no_fila+1 WHERE id_sucursal = %s", (clientes[i]["sucursal"],))
                            self.connection.commit()
                            cur.close()
                            #el cliente elige el producto de la charcutería 
                            cur = self.connection.cursor()
                            if sucursal == 1:
                                cur.execute("SELECT nombre FROM producto_asignado AS A INNER JOIN producto AS P ON A.id_producto = P.id_producto WHERE id_estante = %s", (2,))
                            else:
                                cur.execute("SELECT nombre FROM producto_asignado AS A INNER JOIN producto AS P ON A.id_producto = P.id_producto WHERE id_estante = %s", (10,))
                            self.connection.commit()
                            productos = cur.fetchall()
                            cur.close()
                            #se elige aleatoriamente el producto
                            producto = random.choice(productos)
                            print("El cliente elige el producto: "+str(producto))
                            cur = self.connection.cursor()
                            cur.execute("SELECT id_producto FROM producto WHERE nombre = %s", (producto,))
                            self.connection.commit()
                            id_producto = cur.fetchone()[0]
                            cur.close()
                            #se busca cuánta cantidad restante queda de ese producto 
                            cur = self.connection.cursor()
                            cur.execute("SELECT cantidad_restante FROM producto_asignado WHERE id_producto = %s", (id_producto,))
                            self.connection.commit()
                            cant = cur.fetchone()[0]
                            cur.close()
                            #si la cantidad es igual a cero el producto se acabó
                            if cant == 0:
                                print("El producto se acabó")
                            else:
                                #se elige de manera alteatoria cuánta cantidad de ese producto agarrá
                                cantidad = random.randint(1, cant)
                                print("El cliente compra "+str(cantidad)+" de este producto")
                                #se busca el precio de ese producto
                                cur = self.connection.cursor()
                                cur.execute("SELECT precio FROM cambio_precio WHERE id_producto = %s", (id_producto,))
                                self.connection.commit()
                                precio = cur.fetchone()[0]
                                cur.close()
                                #se mete el producto en su carrito
                                clientes[i]["carrito"].append({
                                    "nombre": producto,
                                    "cantidad": str(cantidad),
                                    "id_producto": id_producto,
                                    "precio": precio
                                })
                                id_estante = int(''.join(map(str, estante)))
                                #se publica el mensaje en el canal correspondiente para indicar que se ha quitado cantidad de un producto en un estante 
                                if sucursal == 1:
                                    self.enviar_mensaje('sucursal1', id_producto, cantidad, id_estante, hora)
                                else:
                                    self.enviar_mensaje('sucursal2', id_producto, cantidad, id_estante, hora)
                                time.sleep(3)
                                #si la alarma de un estante se activó los empleados vuelven a llenar el estante 
                                if self.activar_alarma_estante == True:
                                    cur = self.connection.cursor()
                                    hora = datetime.datetime.now().replace(minute=0, second=0) 
                                    cur.execute("SELECT llenar_estante(%s)", (id_estante, hora,))
                                    self.connection.commit()
                                    cur.close()
                                    self.activar_alarma_estante = False
                        else:
                            #si todavía no es su turno de va a otro pasillo 
                            clientes[i]["currently"] = "ir a un pasillo"
                    else:
                        #si no está en la cola de la charcutería va a un pasillo 
                        clientes[i]["currently"] = "ir a un pasillo"
                if clientes[i]["currently"] == "ir a la charcutería":
                    #el cliente agarra un sensor que puede tener en su carrito que le avisará cuando sea su turno para que lo atiendan 
                    no_fila += 1
                    cur = self.connection.cursor()
                    #se verifica si el cliente es regular y está registrado
                    cur.execute("SELECT verificar_cliente(%s)", (clientes[i]["id_cliente"],))
                    self.connection.commit()
                    is_cliente = cur.fetchone()[0]
                    cur.close()
                    #si no está registrado se guarda su información en la bd
                    if is_cliente == False:
                        cur = self.connection.cursor()
                        cur.execute("INSERT INTO cliente(id_cliente, nombre, apellido, telefono, direccion) VALUES (%s, %s, %s, %s, %s)", (clientes[i]["id_cliente"], clientes[i]["nombre"], clientes[i]["apellido"], clientes[i]["telefono"], clientes[i]["direccion"],))
                        self.connection.commit()
                        cur.close()
                        cur = self.connection.cursor()
                        cur.execute("INSERT INTO cliente_charcuteria(id_cliente, no_fila, id_sucursal) VALUES (%s, %s, %s)", (clientes[i]["id_cliente"], no_fila,clientes[i]["sucursal"],))
                        self.connection.commit()
                        cur.close()
                    #si está registrado se procede a guardarlo en la fila
                    else:
                        cur = self.connection.cursor()
                        cur.execute("INSERT INTO cliente_charcuteria(id_cliente, no_fila, id_sucursal) VALUES (%s, %s, %s)", (clientes[i]["id_cliente"], no_fila,clientes[i]["sucursal"],))
                        self.connection.commit()
                        cur.close()
                    #se publica el mensaje en el canal correspondiente para indicar que se agregó otro cliente a la cola
                    if sucursal == 1:
                        self.enviar_mensaje_sensor('sucursal1', clientes[i]["id_cliente"], clientes[i]["sucursal"])
                    else:
                        self.enviar_mensaje_sensor('sucursal2', clientes[i]["id_cliente"], clientes[i]["sucursal"])
                    time.sleep(3)
                    #si el estado del cliente es ir a un pasillo o seguir viendo
                if clientes[i]["currently"] == "ir a un pasillo" or clientes[i]["currently"] == "sigue viendo":
                    #se elige de manera random a que pasillo se dirigirá el cliente
                    cur = self.connection.cursor()
                    cur.execute("SELECT no_pasillo FROM estante_inteligente WHERE id_sucursal = %s", (sucursal,))
                    self.connection.commit()
                    pasillos = cur.fetchall()
                    cur.close()
                    pasillo = random.choice(pasillos)
                    pasillo = int(''.join(map(str, pasillo)))
                    print("El cliente se dirige al pasillo "+str(pasillo))
                    #se elige de manera aleatoria el estante al que se dirigirá el cliente 
                    cur = self.connection.cursor()
                    cur.execute("SELECT id_estante FROM estante_inteligente WHERE id_sucursal = %s AND no_pasillo = %s AND id_estante NOT IN (2)", (sucursal, pasillo,))
                    self.connection.commit()
                    estantes = cur.fetchall()
                    cur.close()
                    estante = random.choice(estantes)
                    print("El cliente se dirige al estante "+str(estante))
                    #se ejecuta un query para obtener todos los productos que están en ese estante 
                    cur = self.connection.cursor()
                    cur.execute("SELECT nombre FROM producto_asignado AS A INNER JOIN producto AS P ON A.id_producto = P.id_producto WHERE id_estante = %s", (estante,))
                    self.connection.commit()
                    productos = cur.fetchall()
                    cur.close()
                    #se elige de manera alteatoria que producto de ese estante agarrará
                    producto = random.choice(productos)
                    print("El cliente elige el producto: "+str(producto))
                    cur = self.connection.cursor()
                    cur.execute("SELECT id_producto FROM producto WHERE nombre = %s", (producto,))
                    self.connection.commit()
                    id_producto = cur.fetchone()[0]
                    cur.close()
                    #se elige de manera alteatoria cuánta cantidad de ese producto agarrá
                    cur = self.connection.cursor()
                    cur.execute("SELECT cantidad_restante FROM producto_asignado WHERE id_producto = %s", (id_producto,))
                    self.connection.commit()
                    cant = cur.fetchone()[0]
                    cur.close()
                    #si la cantidad es 0 el producto se acabó
                    if cant == 0:
                        print("El producto se acabó")
                    else:
                        #se elige el manera aleatoria la cantidad que agarrará
                        cantidad = random.randint(1, cant)
                        print("El cliente agarra "+str(cantidad)+" de este producto")
                        #se elige de manera aleatoria si el cliente dejará el producto o lo comprará
                        opciones = list(["lo compra"])
                        decision = random.choice(opciones)
                        print("El cliente "+str(decision))
                        if(decision == "lo compra"):
                            cur = self.connection.cursor()
                            #se busca el precio del producto
                            cur.execute("SELECT precio FROM cambio_precio WHERE id_producto = %s", (id_producto,))
                            self.connection.commit()
                            precio = cur.fetchone()[0]
                            cur.close()
                            clientes[i]["carrito"].append({
                                "nombre": producto,
                                "cantidad": str(cantidad),
                                "id_producto": id_producto,
                                "precio": precio
                            })
                            #cuando se agarra un producto de un estante se hace un publish en el canal 
                            #para verificar que no queda el 20% de los productos 
                            #si queda el 20% se activa una alarma y los empleados lo vuelven a llenar
                            id_estante = int(''.join(map(str, estante)))
                            if sucursal == 1:
                                self.enviar_mensaje('sucursal1', id_producto, cantidad, id_estante, hora)
                            else:
                                self.enviar_mensaje('sucursal2', id_producto, cantidad, id_estante, hora)
                            time.sleep(3)
                            if self.activar_alarma_estante == True:
                                cur = self.connection.cursor()
                                cur.execute("SELECT llenar_estante(%s)", (id_estante,))
                                self.connection.commit()
                                cur.close()
                                self.activar_alarma_estante = False
                #se elige de manera aleatoria si el cliente sigue viendo más cosas o va a pagar
                if len(clientes[i]["carrito"]) > 0:
                    opciones = list(["sigue viendo", "va a pagar"])
                    decision = random.choice(opciones)
                    print("El cliente "+str(decision))
                    clientes[i]["currently"] = decision
                else:
                    opciones = list(["sigue viendo", "se va"])
                    decision = random.choice(opciones)
                    print("El cliente "+str(decision))
                    clientes[i]["currently"] = decision
                #si el cliente se va se quita su indice del array
                if clientes[i]["currently"] == "se va":
                    indices.remove(i)
                    cur = self.connection.cursor()
                    cur.execute("SELECT verificar_cola(%s)", (clientes[i]["id_cliente"],))
                    self.connection.commit()
                    is_en_cola = cur.fetchone()[0]
                    cur.close()
                    if is_en_cola == True:
                        #se borra de la fila el cliente
                        cur = self.connection.cursor()
                        cur.execute("DELETE FROM cliente_charcuteria WHERE id_cliente = %s", (clientes[i]["id_cliente"],))
                        self.connection.commit()
                        cur.close()
                        #actualizar fila 
                        cur = self.connection.cursor()
                        cur.execute("UPDATE cliente_charcuteria SET no_fila = cliente_charcuteria.no_fila+1")
                        self.connection.commit()
                        cur.close()
                #si el cliente va a pagar se hace todos el proceso de pago
                if clientes[i]["currently"] == "va a pagar":
                    total = 0 
                    cont_factura += 1
                    cur = self.connection.cursor()
                    #se verifica si el cliente está registrado
                    cur.execute("SELECT verificar_cliente(%s)", (clientes[i]["id_cliente"],))
                    self.connection.commit()
                    is_cliente = cur.fetchone()[0]
                    cur.close()
                    if is_cliente == False:
                        #si no está registrado se registra
                        cur = self.connection.cursor()
                        cur.execute("INSERT INTO cliente(id_cliente, nombre, apellido, telefono, direccion) VALUES (%s, %s, %s, %s, %s)", (clientes[i]["id_cliente"], clientes[i]["nombre"], clientes[i]["apellido"], clientes[i]["telefono"], clientes[i]["direccion"],))
                        self.connection.commit()
                        cur.close()
                        #se calcula el total a pagar
                        for index in range(0, len(clientes[i]["carrito"])):   
                            cur = self.connection.cursor()
                            cur.execute("SELECT precio FROM cambio_precio WHERE id_producto = %s", (clientes[i]["carrito"][index]["id_producto"],))
                            self.connection.commit()
                            precio = cur.fetchone()[0]
                            total += int(''.join(map(str, clientes[i]["carrito"][index]["cantidad"])))*precio
                            cur.close()
                        print("El total a pagar es: "+str(total))
                        cur = self.connection.cursor()
                        #se verifica si pertenece al programa de fidelidad
                        cur.execute("SELECT verificar_pertenece_programa(%s)", (clientes[i]["id_cliente"],))
                        self.connection.commit()
                        pertenece = cur.fetchone()[0]
                        cur.close()
                        cur = self.connection.cursor()
                        if pertenece == True:
                            opciones = list(["Banesco", "Provincial", "Mercantil"])
                            banco = random.choice(opciones)
                            hora = datetime.datetime.now().replace(minute=0, second=0) 
                            cur.execute("SELECT realizar_pago((SELECT no_cuenta FROM cuenta_programa_fidelidad WHERE id_cliente = %s), %s, %s, %s, %s, %s, %s, %s, %s)", (clientes[i]["id_cliente"],clientes[i]["id_cliente"],banco,sucursal,cont_factura,total,0,total,hora,))
                        else:
                            opciones = list(["Banesco", "Provincial", "Mercantil"])
                            banco = random.choice(opciones)
                            cur.execute("SELECT realizar_pago(%s, %s, %s, %s, %s, %s, %s, %s, %s)", (0,clientes[i]["id_cliente"],banco,sucursal,cont_factura,total,0,total,hora,))
                            self.connection.commit()
                            cur.close()
                        #se registran todos los detalles de la factura
                        for index in range(0, len(clientes[i]["carrito"])):   
                            cur = self.connection.cursor()
                            cur.execute("INSERT INTO detalle_factura(id_factura, id_producto, cantidad, subtotal) VALUES (%s, %s, %s, %s)", (cont_factura, clientes[i]["carrito"][index]["id_producto"], clientes[i]["carrito"][index]["cantidad"], clientes[i]["carrito"][index]["precio"]*int(''.join(map(str, clientes[i]["carrito"][index]["cantidad"]))),))
                            self.connection.commit()
                            cur.close()
                    else:
                        #si es cliente regular 
                        for index in range(0, len(clientes[i]["carrito"])):   
                            #se calcula el total
                            cur = self.connection.cursor()
                            cur.execute("SELECT precio FROM cambio_precio WHERE id_producto = %s", (clientes[i]["carrito"][index]["id_producto"],))
                            self.connection.commit()
                            precio = cur.fetchone()[0]
                            total += int(''.join(map(str, clientes[i]["carrito"][index]["cantidad"])))*precio
                            cur.close()
                        print("El total a pagar es: "+str(total))
                        cur = self.connection.cursor()
                        #se verifica si pertenece al programa
                        cur.execute("SELECT verificar_pertenece_programa(%s)", (clientes[i]["id_cliente"],))
                        self.connection.commit()
                        pertenece = cur.fetchone()[0]
                        cur.close()
                        cur = self.connection.cursor()
                        if pertenece == True:
                            opciones = list(["Banesco", "Provincial", "Mercantil"])
                            banco = random.choice(opciones)
                            hora = datetime.datetime.now().replace(minute=0, second=0) 
                            cur.execute("SELECT realizar_pago(%s, (SELECT no_cuenta FROM cuenta_programa_fidelidad WHERE id_cliente = %s), %s, %s, %s, %s, %s, %s, %s)", (clientes[i]["id_cliente"],clientes[i]["id_cliente"],banco,sucursal,cont_factura,total,0,total,hora,))
                        else:
                            opciones = list(["Banesco", "Provincial", "Mercantil"])
                            banco = random.choice(opciones)
                            cur.execute("SELECT realizar_pago(%s, %s, %s, %s, %s, %s, %s, %s, %s)", (0,clientes[i]["id_cliente"],banco,sucursal,cont_factura,total,0,total,hora,))
                            self.connection.commit()
                            cur.close()
                        for index in range(0, len(clientes[i]["carrito"])):   
                            cur = self.connection.cursor()
                            cur.execute("INSERT INTO detalle_factura(id_factura, id_producto, cantidad, subtotal) VALUES (%s, %s, %s, %s)", (cont_factura, clientes[i]["carrito"][index]["id_producto"], clientes[i]["carrito"][index]["cantidad"], clientes[i]["carrito"][index]["precio"]*int(''.join(map(str, clientes[i]["carrito"][index]["cantidad"]))),))
                            self.connection.commit()
                            cur.close()
                if cont_tiempo == 1:
                    #decidir si entrarán más clientes
                    opciones = list(["entran más clientes", "pues no mi ciela"])
                    decision = random.choice(opciones)
                    cont_tiempo = 0
                    print(decision)
                    if(decision == "entran más clientes"):
                        #se eligen varios varios valores aleatorios según la cantidad de clientes que va a entrar 
                        more_clientes = 0
                        cantidad = random.randint(1, 10)
                        print("Cantidad: "+str(cantidad))
                        indices_aux = []
                        values = list(range(0, len(clientes)))#cantidad de clientes en total
                        for j in indices:
                            values.remove(j)
                        for i in range(cantidad):
                            for x in indices_aux:
                                if x in values:
                                    values.remove(x)
                            #se elige un valor random 
                            r1 = random.choice(values)
                            #se guardan los indices seleccionados en el array
                            indices.append(r1)
                            indices_aux.append(r1)
                        print("Entran los siguientes indices de clientes: "+str(indices))
                time.sleep(2)
                #si ya pasaron dos vueltas en el for se aumenta una hora 
                if cont_horas == 2:
                    hora = hora + datetime.timedelta(hours=1)
                    horas += 1
                    #si pasaron 24 horas se aumenta el contador de días 
                    if horas == 24:
                        day += 1
                    

            

