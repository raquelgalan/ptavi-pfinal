#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
# Práctica Final: Raquel Galán Montes
"""
Clase (y programa principal) para un servidor de SIP proxy-registrar en UDP
"""

import SocketServer
import socket
import sys
import os
import time
from xml.sax import make_parser
from xml.sax.handler import ContentHandler
import uaserver


class LogProxy(uaserver.Log):
    """Clase que hereda de Log del servidor"""


class XMLProxy(ContentHandler):
    """
    Clase para leer de un fichero de configuracion XML
    """

    def __init__(self):
        self.dic = {}
        self.etq = {"server", "database", "log"}
        self.atrib = {
            "server": ["name", "ip", "puerto"],
            "database": ["path", "passwdpath"],
            "log": ["path"],
            }

    def startElement(self, name, attrs):
        if name in self.etq:
            for atributo in self.atrib[name]:
                element = name + "_" + atributo
                self.dic[element] = attrs.get(atributo, "")

    def get_tags(self):
        return self.dic


class ProxyHandler(SocketServer.DatagramRequestHandler):
    """
    Registro SIP
    """
    dic_clientes = {}
    error_invite = False
    error_bye = False

    def handle(self):
        """
        Manejador que recibe peticiones SIP del cliente
        (las guarda y confirma si no hay errores)
        """
        # Tipos de respuestas
        Trying = "SIP/2.0 100 Trying\r\n\r\n"
        Ringing = "SIP/2.0 180 Ringing\r\n\r\n"
        OK = "SIP/2.0 200 OK\r\n\r\n"
        Bad = "SIP/2.0 400 Bad Request\r\n\r\n"
        Not_Found = "SIP/2.0 404 User Not Found\r\n\r\n"
        Not_Allowed = "SIP/2.0 405 Method Not Allowed\r\n\r\n"
        Metodos_Aceptados = ["REGISTER", "INVITE", "ACK", "BYE"]

        #Se actualiza del diccionario
        self.caducidad()

        while 1:
            # Leyendo línea a línea lo que nos envía el cliente
            line = self.rfile.read()
            lista = line.split()
            if line != "":
                print "El cliente nos manda: " + line
                metodo = line.split(" ")[0]

                if metodo == "REGISTER":
                    print "Comienza REGISTER"

                    lista_sip = lista[1].split(":")
                    direc = lista_sip[1]
                    puerto = lista_sip[2]
                    #De parte de quien se recibe el mensaje
                    ip = self.client_address[0]
                    pto = self.client_address[1]
                    print "Recibimos desde: " + ip + " " + str(pto)
                    h = time.time()
                    exp = int(lista[4])
                    tot = h + float(exp)

                    log.FichXML(" Received from ", line, ip, pto)

                    if exp == 0:
                        """
                        Si el tiempo de expiración=0, damos de baja al cliente
                        """
                        del self.dic_clientes[direc]

                    else:
                        """
                        Añadimos cliente
                        """
                        self.dic_clientes[direc] = [ip, puerto, h, exp, tot]
                        print "añadido:"
                        print self.dic_clientes[direc]

                    respuesta = " SIP/2.0 200 OK\r\n\r\n"
                    print "Enviando: " + respuesta
                    self.wfile.write(respuesta)
                    log.FichXML(" Sent to ", respuesta, ip, puerto)
                    self.register2file(ip, direc)

                elif metodo == "INVITE":
                    print "Se ha recibido: " + line + "\r\n"
                    print "Comienza INVITE"

                    lista_sip = lista[1].split(":")
                    print "Lista SIP: "
                    print lista_sip
                    direc_receptor = lista_sip[1]

                    #De parte de quien se recibe el mensaje
                    #Quien envia el INVITE
                    ip = self.client_address[0]
                    pto = self.client_address[1]

                    log.FichXML(" Received from ", line, ip, pto)
                    print "Recibimos desde: " + ip + " " + str(pto)
                    #Se busca si el usuario al que se
                    #lo vamos a enviar esta registrado

                    registro_usuario = self.usuario_registrado(direc_receptor)
                    print "registro", registro_usuario
                    if registro_usuario == 0:
                        print "usuario no encontrado"

                        self.wfile.write(Not_Found)
                        log.FichXML(" Sent to ", Not_Found, ip, pto)

                    else:
                        print "Si encontrado"
                        print registro_usuario
                        recep_ip = registro_usuario[0]
                        print "recep_ip", recep_ip
                        recep_pt = registro_usuario[1]
                        print "recep_pt", recep_pt

                        # Abro socket y reenvio el invite a quien va dirigido
                        my_socket = socket.socket(socket.AF_INET,
                                                socket.SOCK_DGRAM)
                        my_socket.setsockopt(socket.SOL_SOCKET,
                                                socket.SO_REUSEADDR, 1)
                        my_socket.connect((recep_ip, int(recep_pt)))

                        print "Reenvio ", line
                        print " a: ", direc_receptor
                        try:
                            my_socket.send(line)
                            print "line", line
                            log.FichXML(" Sent to ", line, recep_ip, recep_pt)
                            # Recibo respuesta de que el destino recibió invite
                            data = my_socket.recv(1024)
                            print "Recibo: ", data
                            log.FichXML(" Received from ", data, recep_ip,
                                                                    recep_pt)
                        except:
                            error_invite = True
                            Sin_servidor = " Error: No server listening "
                            Sin_servidor += recep_ip + " port " + str(recep_pt)
                            print Sin_servidor
                            log.FichXML(Sin_servidor, " ", " ", " ")

                        error_invite = False
                        # Reenvío la respuesta al que envió el invite
                        if not error_invite:
                            self.wfile.write(data)
                            print " Reenvio ", data
                            log.FichXML(" Sent to ", data, ip, pto)
                        else:
                            self.wfile.write(Not_Found)

                    print "Acaba INVITE"

                elif metodo == "ACK":
                    print "Recibido ACK"
                    lista_sip = lista[1].split(":")
                    direc_receptor = lista_sip[1]

                    #De parte de quien se recibe el mensaje
                    #Quien envia el INVITE
                    ip = self.client_address[0]
                    pto = self.client_address[1]

                    log.FichXML(" Received from ", line, ip, pto)

                    registro_usuario = self.usuario_registrado(direc_receptor)

                    if registro_usuario != 0:
                        recep_ip = registro_usuario[0]
                        recep_pt = registro_usuario[1]

                        # Reenvio ACK
                        my_socket = socket.socket(socket.AF_INET,
                                                socket.SOCK_DGRAM)
                        my_socket.setsockopt(socket.SOL_SOCKET,
                                                socket.SO_REUSEADDR, 1)
                        my_socket.connect((recep_ip, int(recep_pt)))

                        my_socket.send(line)
                        print " Reenvio Ack", line
                        log.FichXML(" Sent to ", line, recep_ip, recep_pt)

                    else:
                        print "usuario no encontrado"
                        ip = self.client_address[0]
                        pto = self.client_address[1]

                        self.wfile.write(Not_Found)
                        log.FichXML(" Sent to ", Not_Found, ip, pto)

                elif metodo == "BYE":
                    print "Comienza BYE"
                    lista_sip = lista[1].split(":")
                    # Quien envia el BYE
                    ip = self.client_address[0]
                    pto = self.client_address[1]
                    direc_receptor = lista_sip[1]

                    log.FichXML(" Received from ", line, ip, pto)

                    registro_usuario = self.usuario_registrado(direc_receptor)
                    print registro_usuario

                    if registro_usuario != 0:
                        print "hay usuario"
                        recep_ip = registro_usuario[0]
                        recep_pt = registro_usuario[1]

                        # Abro socket y reenvio el BYE
                        my_socket = socket.socket(socket.AF_INET,
                                                socket.SOCK_DGRAM)
                        my_socket.setsockopt(socket.SOL_SOCKET,
                                                socket.SO_REUSEADDR, 1)
                        my_socket.connect((recep_ip, int(recep_pt)))

                        try:
                            print "Reenviando: ", line
                            my_socket.send(line)
                            log.FichXML(" Sent to ", line, recep_ip, recep_pt)
                            data = my_socket.recv(1024)
                            print "Recibido", data
                            log. FichXML(" Received from ", data, recep_ip,
                                                                    recep_pt)

                        except:
                            error_bye = True
                            Sin_servidor = " Error: No server listening "
                            Sin_servidor += recep_ip + " port " + str(recep_pt)
                            print Sin_servidor
                            log.FichXML(Sin_servidor, " ", " ", " ")

                        error_invite = False
                        # Reenvío la respuesta al que envió el bye
                        if not error_invite:
                            self.wfile.write(data)
                            print "enviando respuesta " + data
                            log.FichXML(" Sent to ", data, ip, pto)
                        else:
                            self.wfile.write(Not_Found)

                    else:
                        print "usuario no encontrado"
                        ip = self.client_address[0]
                        pto = self.client_address[1]

                        self.wfile.write(Not_Found)
                        log.FichXML(" Sent to ", Not_Found, ip, pto)

                    print "Acaba BYE"

                elif metodo not in Metodos_Aceptados:
                    print "metodo incorrecto"
                    ip = self.client_address[0]
                    pto = self.client_address[1]

                    self.wfile.write(Not_Allowed)
                    log.FichXML(" Sent to ", Not_Allowed, ip, pto)

                else:
                    print "peticion mal formada"
                    ip = self.client_address[0]
                    pto = self.client_address[1]

                    self.wfile.write(Bad)
                    log.FichXML(" Sent to ", Bad, ip, pto)

            # Si no hay más líneas salimos del bucle infinito
            else:
                break

    def register2file(self, ip, direc):
        """
        Si un usuario se registra o se va, se pone en usuarios_registrados.txt
        """
        fich = open(PR_PATH, "w")
        fich.write("User\tIP\t\t\tPort\tFecha Registro\tExpires\r\n")

        for usuario in self.dic_clientes:
            ip = self.dic_clientes[usuario][0]
            port = self.dic_clientes[usuario][1]
            registro = int(self.dic_clientes[usuario][2])
            exp = str(self.dic_clientes[usuario][3])
            fecha = time.strftime('%Y%m%d%H%M%S', time.gmtime(registro))
            valores = usuario + "\t" + ip + "\t" + str(port) + "\t"
            valores += str(registro) + "\t\t" + exp + "\r\n"
            fich.write(valores)

    def caducidad(self):
        """
        Actualiza el diccionario, eliminando
        usuarios con el plazo expirado
        """
        lista = []
        for usuario in self.dic_clientes:
            print self.dic_clientes
            if time.time() >= self.dic_clientes[usuario][4]:
                print "marco el usuario: ", usuario
                lista.append(usuario)

        for usuario in lista:
            print "borrado:", usuario
            del dic_clientes[usuario]

    def usuario_registrado(self, user):
        """
        Verifica si el usuario esta registrado
        """
        if user in self.dic_clientes.keys():
            datos_user = self.dic_clientes[user]
            return datos_user
        else:
            return 0


if __name__ == "__main__":

    try:
        # Verificar argumento
        #fichero xml
        CONFIG = sys.argv[1]

        # Sacamos datos del xml
        parser = make_parser()
        cHandler = XMLProxy()
        parser.setContentHandler(cHandler)

        # os.path.exists solo devuelve True si hay un fichero con ese nombre
        if os.path.exists(CONFIG) is False:
            print "No hay un fichero con ese nombre"
            raise SystemExit

        parser.parse(open(CONFIG))
        dic = cHandler.get_tags()

        # Sale error si le introducimos argumentos de más
        parametros = len(sys.argv)
        if parametros != 2:
            print "argumentos"
            raise SystemExit

        # Nombrar elementos del diccionario
        PR_NAME = dic["server_name"]
        PR_IP = dic["server_ip"]
        PR_PTO = int(dic["server_puerto"])
        PR_PATH = dic["database_path"]
        PR_PASSWDPATH = dic["database_passwdpath"]
        PR_LOG = dic["log_path"]

        # Creamos el log
        log = LogProxy(PR_LOG)
        log.FichXML(" Starting...", "", "", "")

        # Creamos servidor SIP y escuchamos
        prox = SocketServer.UDPServer(("", PR_PTO), ProxyHandler)

        print "Server ", PR_NAME, " listening at port ", str(PR_PTO), "...\r\n"
        prox.serve_forever()

    except:
        print ("Usage: python proxy_registrar.py config")
        raise SystemExit
