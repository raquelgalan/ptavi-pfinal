#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
# Práctica Final: Raquel Galán Montes
"""
Programa cliente que abre un socket a un servidor
"""

import socket
import sys
import os
import time
from xml.sax import make_parser
from xml.sax.handler import ContentHandler
import uaserver


class XMLClient(uaserver.XMLHandler):
    """Clase que hereda de XMLHandler"""


class LogClient(uaserver.Log):
    """Clase que hereda de Log del servidor"""


if __name__ == "__main__":

    # Sacamos datos del xml
    parser = make_parser()
    cHandler = XMLClient()
    parser.setContentHandler(cHandler)

    # Verificar los argumentos
    #fichero xml
    CONFIG = sys.argv[1]
    #metodo SIP
    METODO = sys.argv[2]

    try:
        # os.path.exists solo devuelve True si hay un fichero con ese nombre
        if os.path.exists(CONFIG) is False:
            print ("No existe ese nombre de fichero XML")
            raise SystemExit

        parser.parse(open(CONFIG))
        dic = cHandler.get_tags()

        # Para ver si no existe el nombre del archivo de audio
        AUDIO_PATH = dic["audio_path"]
        if not os.path.exists(AUDIO_PATH):
            print "no existe ningun archivo de audio con ese nombre"
            raise SystemExit

        #Sale error si le introducimos argumentos de más
        parametros = len(sys.argv)
        if parametros != 4:
            print ("numero de parametros")
            raise SystemExit

        # Sale error si no coincide con los metodos register, invite o bye
        if METODO == "REGISTER":
            OPCION = int(sys.argv[3])
        elif METODO == "INVITE" or METODO == "BYE":
            OPCION = sys.argv[3]
        else:
            print "metodo desconocido"
            raise SystemExit

    except ValueError:
        print ("Usage: si metodo = REGISTER el ultimo argumento = entero")
        raise SystemExit

    except:
        print ("Usage: python uaclient.py config method option")
        raise SystemExit

    # Creamos el log
    LOG_PATH = dic["log_path"]
    log = LogClient(LOG_PATH)

    # Nombrar elementos del fichero XML
    USERNAME = dic["account_username"]
    UASERVER_IP = dic["uaserver_ip"]
    UASERVER_PTO = int(dic["uaserver_puerto"])
    RTPAUDIO_PTO = int(dic["rtpaudio_puerto"])
    REGPROXY_IP = dic["regproxy_ip"]
    REGPROXY_PTO = int(dic["regproxy_puerto"])

    # Contenido que vamos a enviar con cada metodo
    if METODO == "REGISTER":
        # Escribimos lo que lleva el log
        log.FicheroXML(" Starting...", "", "", "")

        LINE = METODO + " sip:" + USERNAME + ":" + str(UASERVER_PTO)
        LINE += " SIP/2.0\r\n" + "Expires: " + str(OPCION) + "\r\n\r\n"
        REGPROXY_IP = dic["regproxy_ip"]
        REGPROXY_PTO = int(dic["regproxy_puerto"])

        # Verificar el servidor y el puerto
        try:
            # Creamos el socket y lo configuramos
            my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Atamos socket a un servidor/puerto
            my_socket.connect((REGPROXY_IP, REGPROXY_PTO))
            print "Enviando: " + LINE
            my_socket.send(LINE + "\r\n ")
            log.FicheroXML(" Sent to ", LINE, REGPROXY_IP, REGPROXY_PTO)

            data = my_socket.recv(1024)
            print "Recibido ", data
            print "data", data
            log.FicheroXML(" Received from ", data, REGPROXY_IP, REGPROXY_PTO)

        except:
            Sin_servidor = " Error: No server listening at " + REGPROXY_IP
            Sin_servidor += " port " + str(REGPROXY_PTO)
            print Sin_servidor
            log.FicheroXML(Sin_servidor, " ", " ", " ")
            raise SystemExit

        print "Terminando socket..."
        my_socket.close()
        print "Fin."
        log.FicheroXML(" Finishing.", " ", " ", " ")

    elif METODO == "INVITE":
        LINE = METODO + " sip:" + OPCION + " SIP/2.0\r\n"
        LINE += "Content-Type: application/sdp\r\n\r\n"
        LINE += "v=0\r\n" + "o=" + USERNAME + " " + UASERVER_IP + "\r\n"
        LINE += "s=misesion\r\n""t=0\r\n" + "m=audio " + str(RTPAUDIO_PTO)
        LINE += " RTP\r\n\r\n"

        # Para ver si no existe el nombre del archivo de audio
        AUDIO_PATH = dic["audio_path"]
        if not os.path.exists(AUDIO_PATH):
            print "no existe ningun archivo con ese nombre de audio"
            raise SystemExit

        # Verificar el servidor y el puerto
        try:
            # Creamos el socket y lo configuramos
            my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Atamos socket a un servidor/puerto
            REGPROXY_IP = dic["regproxy_ip"]
            REGPROXY_PTO = int(dic["regproxy_puerto"])
            my_socket.connect((REGPROXY_IP, REGPROXY_PTO))
            connect_info = "Conectando a :" + REGPROXY_IP + " "
            connect_info += str(REGPROXY_PTO)
            print connect_info
            print "Enviando: " + LINE
            my_socket.send(LINE + "\r\n ")
            log.FicheroXML(" Sent to ", LINE, REGPROXY_IP, REGPROXY_PTO)
            data2 = my_socket.recv(1024)
            print "Recibido ", data2
            print "data2", data2
            log.FicheroXML(" Received from ", data2, REGPROXY_IP, REGPROXY_PTO)

            #ACK
            # Si se recibe 100, 180 y 200 se envia ACK con el contenido
            datos = data2.split()
            print datos
            if datos[1] == "100" and datos[4] == "180" and datos[7] == "200":
                METODO = "ACK"
                LINE = METODO + " sip:" + OPCION + " SIP/2.0\r\n\r\n"
                print "Enviando: " + LINE + "\r\n"
                my_socket.send(LINE + "\r\n ")
                log.FicheroXML(" Sent to ", LINE, REGPROXY_IP, REGPROXY_PTO)

                #RTP
                os.system("chmod 777 mp32rtp")
                RECEPTOR_IP = datos[13]
                print "receptor_ip", RECEPTOR_IP
                RECEPTOR_PTO = datos[17]
                print "receptor_pto", RECEPTOR_PTO
                AUDIO_PATH = dic["audio_path"]
                aEjecutar = "./mp32rtp -i " + RECEPTOR_IP + " -p "
                aEjecutar += str(RECEPTOR_PTO) + " < " + AUDIO_PATH
                print "Vamos a ejecutar", aEjecutar, "\r\n"
                os.system(aEjecutar)
                log.FicheroXML(" RTP ", " ", " ", " ")
                print "Fin RTP: Audio enviado" + "\r\n"

            print "Terminando socket..."
            my_socket.close()
            print "Fin."
            log.FicheroXML(" Finishing.", " ", " ", " ")

        except:
            Sin_servidor = " Error: No server listening at " + REGPROXY_IP
            Sin_servidor += " port " + str(REGPROXY_PTO)
            print Sin_servidor
            log.FicheroXML(Sin_servidor, " ", " ", " ")
            raise SystemExit

    elif METODO == "BYE":
        LINE = METODO + " sip:" + OPCION + " SIP/2.0\r\n\r\n"

        # Verificar el servidor y el puerto
        try:
            # Creamos el socket y lo configuramos
            my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Atamos socket a un servidor/puerto
            REGPROXY_IP = dic["regproxy_ip"]
            REGPROXY_PTO = int(dic["regproxy_puerto"])
            my_socket.connect((REGPROXY_IP, REGPROXY_PTO))
            print "Enviando: " + LINE
            my_socket.send(LINE + "\r\n ")
            log.FicheroXML(" Sent to ", LINE, REGPROXY_IP, REGPROXY_PTO)

            data3 = my_socket.recv(1024)
            print "Recibido ", data3
            print "data3", data3
            log.FicheroXML(" Received from ", data3, REGPROXY_IP, REGPROXY_PTO)

            if data3 == "SIP/2.0 200 OK":
                print "Terminando socket..."
                my_socket.close()
                print "Fin."
                log.FicheroXML(" Finishing.", " ", " ", " ")

        except:
            Sin_servidor = " Error: No server listening at " + REGPROXY_IP
            Sin_servidor += " port " + str(REGPROXY_PTO)
            print Sin_servidor
            log.FicheroXML(Sin_servidor, " ", " ", " ")
            raise SystemExit
