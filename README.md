# transmissionline_generator
Generates Parameterizable Transmission Line Layouts in KLayout

## Steps to Generate and Simulate a Transmission Line
1. Run the transmission line generator script in klayout
2. Open up ansysedt (for reference, for me this is)

```
cd {MY_WORKING_DIR}/hfss
source .bashrc
ansysedt
```
3. Project → Insert HFSS Design
4. Modeler→Import→ Select your gds file, change to script, and import
5. Run the build_tl.py script to thicken and build the PCB as well as build the ports on the ends. You will likely need to create your own scripts based on your own stackups, the build_tl.py script is based on my stackup defined in the tech folder
6. Take the unassigned ports, and assign them to be lumped ports, and then assign the integration line from bottom (m1) to top (m2) on the plane of the port
7. Change the simulation parameters
