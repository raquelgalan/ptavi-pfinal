#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
# Práctica Final: Raquel Galán Montes
"""
Clase (y programa principal) para un servidor SIP
"""

import SocketServer
import socket
import sys
import os
import time
from xml.sax import make_parser
from xml.sax.handler import ContentHandler


class XMLHandler(ContentHandler):
    """
    Clase para leer de un fichero de configuracion XML
    """

    def __init__(self):
        """
        Constructor
        """
        self.dic = {}
        self.etq = {"account", "uaserver", "rtpaudi", "rgprox", "log", "audi"}
        self.atrib = {
            "account": ["username", "passwd"],
            "uaserver": ["ip", "puerto"],
            "rtpaudi": ["puerto"],
            "rgprox": ["ip", "puerto"],
            "log": ["path"],
            "audi": ["path"]
            }

    def startElement(self, name, attrs):
        """
        A cada elemento le une su etiqueta con sus atributos
        """
        if name in self.etq:
            for atributo in self.atrib[name]:
                element = name + "_" + atributo
                self.dic[element] = attrs.get(atributo, "")

    def get_tags(self):
        """
        Devuelve elementos del diccionario
        """
        return self.dic


class Log():
    """
    Escribe lo que ocurre en el UA
    """

    def __init__(self, fich):
        self.fich = fich

    def FichXML(self, evento, datos, ip, port):
        """
        Se forma cada linea separada con espacios para cada caso
        """
        fich_log = open(self.fich, "a")
        t = time.strftime("%Y%m%d%H%M%S", time.gmtime(time.time()))

        line = datos.split()
        line = " ".join(line)

        if evento != " Starting..." and evento != " Finishing.":
            linea_log = t + evento + ip + ":" + str(port) + ": "
            linea_log += line + '\r\n'
            fich_log.write(linea_log)

        elif evento == "Error":
            linea_log = t + evento + '\r\n'
            fich_log.write(linea_log)
        else:
            linea_log = t + evento + '\r\n'
            fich_log.write(linea_log)

        fich_log.close()


class SIPHandler(SocketServer.DatagramRequestHandler):
    """
    SIP server class
    """
    def handle(self):
        #Tipos de respuestas:
        Not_Allowed = "SIP/2.0 405 Method Not Allowed\r\n\r\n"
        Bad = "SIP/2.0 400 Bad Request\r\n\r\n"
        while 1:
            # Leyendo línea a línea lo que nos envía el cliente
            line = self.rfile.read()
            ip = self.client_address[0]
            pto = self.client_address[1]

            if line != "":
                lista = line.split()
                username = lista[1]
                sip_username = username.split(":")[0]
                version_sip = lista[2]
                if sip_username == "sip" and version_sip == "SIP/2.0":
                    print "El proxy nos manda: " + line
                    metodo = line.split(" ")[0]

                    #log
                    dic = cHandler.get_tags()
                    LOG_PATH = dic["log_path"]
                    log = Log(LOG_PATH)

                    log.FichXML(" Received from ", line, RGPROX_IP, RGPROX_PT)

                    if metodo == "INVITE":
                        print "Se ha recibido: " + line + "\r\n"
                        print "Comienza INVITE"
                        # Se forma line con 100, 180, 200
                        line = "SIP/2.0 100 Trying\r\n\r\n"
                        line += "SIP/2.0 180 Ringing\r\n\r\n"
                        line += "SIP/2.0 200 OK\r\n\r\n"

                        cuerpo = line + "Content-Type: application/sdp\r\n\r\n"
                        cuerpo += "v=0\r\n" + "o=" + USERNAME + " "
                        cuerpo += UASERVER_IP + "\r\n" + "s=misesion\r\n"
                        cuerpo += "t=0\r\n" + "m=audio " + str(RTPAUDIO_PTO)
                        cuerpo += " RTP\r\n\r\n"

                        print "Envio: " + cuerpo
                        self.wfile.write(cuerpo)

                        log.FichXML(" Sent to ", cuerpo, RGPROX_IP, RGPROX_PT)

                        print "Acaba INVITE"

                    elif metodo == "ACK":
                        print "Se recibe ACK y empieza RTP"
                        #Se recibe ACK y empieza RTP

                        os.system("chmod 777 mp32rtp")

                        aEjecutar = "./mp32rtp -i " + RGPROX_IP + " -p "
                        aEjecutar += str(RTPAUDIO_PTO) + " < " + AUDIO_PATH
                        print "Vamos a ejecutar", aEjecutar
                        os.system(aEjecutar)

                        print "ip", ip
                        print "uaserver_ip", UASERVER_IP
                        print "pto", pto

                        log.FichXML(" Envio RTP ", " ", " ", " ")

                        print "Fin RTP: Audio enviado>>>>>>>"
                        print "Acaba RTP"

                    elif metodo == "BYE":
                        print "Comienza BYE"
                        line = "SIP/2.0 200 OK\r\n\r\n"
                        self.wfile.write(line)
                        print "responde al BYE " + line

                        log.FichXML(" Sent to ", line, ip, pto)
                        log.FichXML(" Finishing. ", " ", " ", " ")

                        print "Acaba BYE"
                    else:
                        # Aqui no se llegaria porque en el cliente lo para
                        print "metodo incorrecto"
                        line = Not_Allowed
                        self.wfile.write(line)
                        log.FichXML(" Sent to ", line, ip, pto)
                        raise SystemExit

                else:

                    # Aqui no se llegaria porque en el cliente lo para
                    print "peticion mal formada"
                    line = Bad
                    self.wfile.write(line)
                    raise SystemExit

            # Si no hay más líneas salimos del bucle infinito
            else:
                break


if __name__ == "__main__":
    dic_rtp = {}

    try:
        # Verificar argumento
        #fichero xml
        CONFIG = sys.argv[1]

        # Sacamos datos del xml
        parser = make_parser()
        cHandler = XMLHandler()
        parser.setContentHandler(cHandler)

        parser.parse(open(CONFIG))
        dic = cHandler.get_tags()

        # os.path.exists solo devuelve True si hay un fichero con ese nombre
        if os.path.exists(CONFIG) is False:
            print "no existe ese nombre de fichero XML"
            raise SystemExit

        # Para ver si no existe el nombre del archivo de audio
        AUDIO_PATH = dic["audi_path"]
        if not os.path.exists(AUDIO_PATH):
            print "no existe ningun archivo de audio con ese nombre"
            raise SystemExit

        # Nombrar elementos del fichero XML
        USERNAME = dic["account_username"]
        UASERVER_IP = dic["uaserver_ip"]
        UASERVER_PTO = int(dic["uaserver_puerto"])
        RTPAUDIO_PTO = int(dic["rtpaudi_puerto"])
        RGPROX_IP = dic["rgprox_ip"]
        RGPROX_PT = int(dic["rgprox_puerto"])

        # Creamos servidor y escuchamos
        serv = SocketServer.UDPServer((UASERVER_IP, UASERVER_PTO), SIPHandler)

        print "Listening..."
        serv.serve_forever()

    except:
        print ("Usage: python uaserver.py config")
        raise SystemExit
