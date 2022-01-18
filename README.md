# OctoPrint-Crealitycloud
![main.png](https://cdn.nlark.com/yuque/0/2022/png/22795356/1642471464755-f2818b50-20a2-4b88-8dcd-ac3a56c80654.png#clientId=u473873a0-7629-4&crop=0&crop=0&crop=1&crop=1&from=drop&id=ub6c0b987&margin=%5Bobject%20Object%5D&name=main.png&originHeight=631&originWidth=700&originalType=binary&ratio=1&rotation=0&showTitle=false&size=443430&status=done&style=none&taskId=u403a724d-b949-42c7-90ae-1a1b334eeb7&title=)
Creality Cloud plugin needs to be installed in the OctoPrint interface so that you can connect the Creality Cloud APP to the Raspberry Pi device and print or control directly through the APP by operating OctoPrint.


## **Setup Creality Cloud Plugin on OctoPrint:**


1. Copy the following three plugin links or copy them from Creality Cloud Github.



Creality Cloud Plugin:


- [https://github.com/crealitycloud/OctoPrint-Crealitycloud/archive/master.zip](https://github.com/crealitycloud/OctoPrint-Crealitycloud/archive/master.zip)



Plugins that the Creality Cloud Plugin relies on:
**Required installation or it may cause abnormal temperature or incomplete functionality:**


- [https://github.com/SimplyPrint/OctoPrint-Creality2xTemperatureReportingFix/archive/master.zip](https://github.com/SimplyPrint/OctoPrint-Creality2xTemperatureReportingFix/archive/master.zip)
- [https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/releases/download/1.26.0/master.zip](https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/releases/download/1.26.0/master.zip)



2. Paste and install the plugin links one by one via the bundled "Plugin Manager" on OctoPrint.

![Setup2-1.png](https://cdn.nlark.com/yuque/0/2022/png/22795356/1642471526539-40ed1264-e4d4-41b8-8a58-da74477bb28f.png#clientId=u473873a0-7629-4&crop=0&crop=0&crop=1&crop=1&from=drop&id=ub29fdff4&margin=%5Bobject%20Object%5D&name=Setup2-1.png&originHeight=554&originWidth=700&originalType=binary&ratio=1&rotation=0&showTitle=false&size=80321&status=done&style=none&taskId=u40475215-6d88-4d86-bf78-b11972b0baf&title=)
![Setup2-2.png](https://cdn.nlark.com/yuque/0/2022/png/22795356/1642471535104-1a5bcca0-f2d1-42c1-91ab-efa9dc7d2a64.png#clientId=u473873a0-7629-4&crop=0&crop=0&crop=1&crop=1&from=drop&id=u4ac0df39&margin=%5Bobject%20Object%5D&name=Setup2-2.png&originHeight=613&originWidth=738&originalType=binary&ratio=1&rotation=0&showTitle=false&size=137115&status=done&style=none&taskId=ufd1e6fda-5ce7-4d3f-ba08-0ff07c6508d&title=)

3. Restart the OctoPrint server when you get a prompt.

![Setup3.png](https://cdn.nlark.com/yuque/0/2022/png/22795356/1642471540555-f4bd0b8a-de87-4206-999a-35f7e6da8916.png#clientId=u473873a0-7629-4&crop=0&crop=0&crop=1&crop=1&from=drop&id=u3beba962&margin=%5Bobject%20Object%5D&name=Setup3.png&originHeight=710&originWidth=1088&originalType=binary&ratio=1&rotation=0&showTitle=false&size=158251&status=done&style=none&taskId=uc2f87981-c791-4260-8582-4535f5c8ae5&title=)
## **Generate A Key File in Creality Cloud APP:**


1. Download and open the Creality Cloud APP on your phone, select "Printing" > click the "+" icon to add device > choose "Raspberry Pi" > click "Create Raspberry Pi" > click "Download Key File".
1. Transmit the Key file to your computer.

![generateKey2-1.png](https://cdn.nlark.com/yuque/0/2022/png/22795356/1642472400478-ec3dc6d5-b0ef-44b5-be25-a7e8b6aeef3a.png#clientId=ua2b85e21-0c9e-4&crop=0&crop=0&crop=1&crop=1&from=drop&id=u3a745b9e&margin=%5Bobject%20Object%5D&name=generateKey2-1.png&originHeight=590&originWidth=700&originalType=binary&ratio=1&rotation=0&showTitle=false&size=207623&status=done&style=none&taskId=u65e54369-3592-41c3-b17b-69b94574760&title=)
![generateKey2-2.png](https://cdn.nlark.com/yuque/0/2022/png/22795356/1642471597807-19f4564a-809d-423f-b10c-af0f4b382a65.png#clientId=u473873a0-7629-4&crop=0&crop=0&crop=1&crop=1&from=drop&id=u341045ae&margin=%5Bobject%20Object%5D&name=generateKey2-2.png&originHeight=776&originWidth=840&originalType=binary&ratio=1&rotation=0&showTitle=false&size=289945&status=done&style=none&taskId=uca8cf6be-9d78-43bc-81af-0c6312cb84a&title=)
## **Upload the Key File to OctoPrint:**


Back to the OctoPrint interface on your desktop, click on the OctoPrint setting button > find the "Crealitycloud Plugin" on the left column list > click "Browse" to select and upload the Key file that you transmitted from Creality Cloud APP.
![uploadKey.png](https://cdn.nlark.com/yuque/0/2022/png/22795356/1642471605360-840b996d-5166-4a7d-9212-1ed8f4c08424.png#clientId=u473873a0-7629-4&crop=0&crop=0&crop=1&crop=1&from=drop&id=u60f3a00f&margin=%5Bobject%20Object%5D&name=uploadKey.png&originHeight=813&originWidth=930&originalType=binary&ratio=1&rotation=0&showTitle=false&size=92449&status=done&style=none&taskId=uf1d96ac0-95df-4b59-adb1-726693a1829&title=)
## **Slice & Print:**


Before you start...


1. Connect your 3D printer with your Raspberry Pi through a USB cable. Here we recommend using a Raspberry Pi 3.
1. Select the USB serial port detected by OctoPrint to connect to your printer.

![slice&print2-1.png](https://cdn.nlark.com/yuque/0/2022/png/22795356/1642471622208-5bfa5c1f-7008-4ca3-bf1c-31851449a1ec.png#clientId=u473873a0-7629-4&crop=0&crop=0&crop=1&crop=1&from=drop&id=u3e7e3392&margin=%5Bobject%20Object%5D&name=slice%26print2-1.png&originHeight=476&originWidth=683&originalType=binary&ratio=1&rotation=0&showTitle=false&size=573994&status=done&style=none&taskId=u58084822-ecbf-437a-a1fd-ab23a70088e&title=)
![slice&print2-2.png](https://cdn.nlark.com/yuque/0/2022/png/22795356/1642471630607-fdc26a21-671d-4508-9bf2-0d93548ddef3.png#clientId=u473873a0-7629-4&crop=0&crop=0&crop=1&crop=1&from=drop&id=u9f653d31&margin=%5Bobject%20Object%5D&name=slice%26print2-2.png&originHeight=328&originWidth=700&originalType=binary&ratio=1&rotation=0&showTitle=false&size=110665&status=done&style=none&taskId=uce6dae09-43c5-498d-b467-56da3632f61&title=)
Start slicing and printing...


1. Open Creality Cloud APP, select My Devices > Raspberrypi (a custom device name)> Select slice.

![slicing&printing1.png](https://cdn.nlark.com/yuque/0/2022/png/22795356/1642471636450-62ef97c1-1934-4d59-8bf0-20368115fcb0.png#clientId=u473873a0-7629-4&crop=0&crop=0&crop=1&crop=1&from=drop&id=u1a54d252&margin=%5Bobject%20Object%5D&name=slicing%26printing1.png&originHeight=758&originWidth=974&originalType=binary&ratio=1&rotation=0&showTitle=false&size=366674&status=done&style=none&taskId=ub4044c3f-89cc-49a2-8a43-d702e0d21fb&title=)

2. Choose a model file to slice and start printing.

![slicing&printing2.png](https://cdn.nlark.com/yuque/0/2022/png/22795356/1642471649704-68e7cb4a-f39a-4090-a4f8-44c801f4c8d1.png#clientId=u473873a0-7629-4&crop=0&crop=0&crop=1&crop=1&from=drop&id=ude3ac464&margin=%5Bobject%20Object%5D&name=slicing%26printing2.png&originHeight=790&originWidth=766&originalType=binary&ratio=1&rotation=0&showTitle=false&size=296681&status=done&style=none&taskId=u2181775c-22dd-41d4-bacc-6144cf8d1cf&title=)
Hope this Creality Cloud plugin on OctoPrint will give you a different experience on your 3D printing. Thank you for supporting and happy printing!


By Creality Cloud.
