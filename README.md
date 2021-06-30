# Smart Campus UMA

El plan propio Smart-Campus I es un proyecto impulsado por la **Universidad de Málaga**   en el que se desarrollan un conjunto de trabajos enfocados  
a potenciar las Smart-Cities. Dos de esos trabajos asignados al mismo equipo de investigación son:

- **DIAS2P** o *Dispositivo Inteligente de Asistencia en Seguridad para Paso de Peatones*.
- **StreetQR**: Dispositivo de control de movimiento de viandantes con emisión de información.

### ¿En qué consiste el DIAS2P?

En este repositorio se presenta el primero de ellos. Un Dispositivo de seguridad enfocado a cruces de peatones sin señalización.
Segun la DGT la mayor parte de los accidentes se producen en pasos a nivel no señalizados, por lo que, con el objetivo de reducir el número de víctimas
se plantea un prototipo que busca reducir la siniestralidad.

|  Visión Delantera  | Visión Trasera |
|---| --- |
|  ![DIAS2P_2.png](images/Design/DIAS2P_2.png) | ![DIAS2P_1.png](images/Design/DIAS2P_1.png) |



A través de reconocimiento de imágenes con Redes Neuronales se detecta la presencia de vehículos y peatones de manera que ante la posibilidad de
que ambos se encuentren en el paso de cebra se activa un sistema de luces y alarmas que alertan de este hecho. Para ello se ha desarrollado un algoritmo de
tracking basado en superficie que monitorea la posición de cada objeto dentro de la imagen.

![Track_01.png](images/Machine%20Learning/Track_01.png)
![Track_02.png](images/Machine%20Learning/Track_02.png)

## Setup

The app can be run from a desktop manager; then you can dynamically configure
road and crosswalk cameras and areas within the cameras' field of view, before
actually starting the inference and the warning logic.

This is, of course, quite inconvenient for unattended usage, because you NEED
to be able to run and forget. To this end, the configuration can be saved (to
*.npy files for areas within cameras' FOV and configuration values for camera
indexes within main.py). You can then configure this app as a systemd service
that will be started automatically upon reboot, and restarted if crashed.

A mild annoyance: our current protetypes use what I suppose are dirt-cheap USB
cameras whose ID_SERIAL numbers are all the same (not seriously, thats DUMB),
so we have NO WAY to configure udev so each index corresponds unequivocally
to each camera. Even worse: the camera index assignment varies across reboots,
sometimes even mixing up the indexes of the onboard camera and the other USB
cameras. Unless we use cameras with different ID_SERIAL strings, THERE IS NO
WAY TO LEAVE THIS FULLY UNATTENDED. All that can be done is to mitigate the
issues about app crashes.


