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
indexes within `main.py`). You can then configure this app as a systemd service
that will be started automatically upon reboot, and restarted if crashed.

A mild annoyance: our current prototypes use what I suppose are USB
cameras whose `ID_SERIAL` numbers are all the same (alas, engineering!),
so we have NO WAY to configure udev so each index corresponds unequivocally
to each camera. Even worse: the camera index assignment varies across reboots,
sometimes even mixing up the indexes of the onboard camera and the other USB
cameras. The way around this is to set up the cameras to be used by usb path

Anyway, THER IS NO WAY TO LEAVE THIS FULLY UNATTENDED, because ocasionally gStreamer
will fail to set up its pipeline, and there is currently no fully automated way around this.
All that can be done is to mitigate the issues about app crashes.

Currently, if started as a systemd daemon, the app will save snapshots from the
cameras at startup with a fixed name, and will save additional snapshots everytime
a file named `gimmeit` is created in its working directory (the one hosting main.py).

## Running as a service in Jetson TX2

First, you have to run the app (`main.py`) in a Desktop (and with `INTERACTIVE_SETUP` set to `True`
in `main.py`) in order to see which camera is facing the road and which one is facing the
crosswalk (and configuring accordingly `'byPathRoad'` and `'byPathCrosswalk'` in the `videoConfig`
dictionary in `main.py`). Also, you have to define the crosswalk areas as asked by the script.

After that, you can use the following commands to start the app as a daemon service:

```
# This has to be done just once at the beginning,
# because if the service is enabled,
# it will start automatically after rebooting
sudo systemctl enable DIAS2P.service
# This has to be done to actually start the service
# after enabling it, if you do not want to reboot
sudo systemctl start DIAS2P.service
```

However, out prototype is somewhat finicky, and gStreamer sometimes fails to set up the pipelines.
You can check the last segment of the daemon's logs with this command:

```
sudo journalctl -u DIAS2P.service -e
```

In daemon mode, the app will log the FPS rate every minute, and it might log hundreds of
`jetson.inference -- PyDetection_Dealloc()` messages per minute. If gStreamer fails to
set up the pipelines, this will not happen, and 30 seconds after starting up, systemd will
kill and restart `main.py` (this is dutifully logged by systemd in the same logs;
just remember that journalctl does not update the logs it displays to you,
so you have to quit journalctl and run it again in order to see new logs).
If you see this happening, please stop the daemon:

```
sudo systemctl stop DIAS2P.service
```

Sometimes, the app will work as a daemon if you have just suceeded in running it from the command line, directly, like this:

```
cd ~/Desktop/DIAS2P
# you may need to prefix the following command with sudo, depending on the setup
python3 main.py
```

If the app runs normally (logging FPS rate and lots of `PyDetection_Dealloc` message every frame),
you can stop it and try to start again the daemon. If it doesn't (or the daemon still refuses
to work), you can reboot and try again. Be aware that after enabling the service, it will always
start up on every reboot until you disable it, and the first run after booting up may fail
because it may start before the cameras and the filesystem are fully ready,
but it should work normally after systemd kills the app and restarts it for the first time
(if not, stop it and try again the previous procedure).


## Recording video

There is another daemon service to record video from both cameras, aptly named recordVideos.
It will record video and save it in ~1 minute mp4 clips encoded in x264.
Gstreamer will be used for this, but ffmepg may be also used. There is one ugly showstopper:
the Jetson TX2 board will require a screen to be connected to record video.
This happens both with gstreamer and ffmpeg, but only when encoding video
instead of just showing it up in a window in the Desktop
(if headless, a Jetson TX2 will set up a small virtual screen and will boot up to Desktop).
I am chalking this up to some insane hack put together in some low-level layer related
to video handling by NVidia.


