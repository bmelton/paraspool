# Paraspool

A parametric cardboard rim adapter that is designed to be filament friendly, truly universal, and to accommodate any rim size you can think of that fits into an AMS (that part is your problem.)

It accepts a number of arguments, but the important ones are spool_diameter, tolerance, and label_text. What's worked well for me so far is just measuring the spool with a tape measure and then trying to print that exact number, then with a tolerance of 0.4. There are 'bundles' for known good values that have printed successfully, so in Customizers, you can just select (eg) "AICOPYTO" if you're using Aicopyto spools, and it should build a good part. What I have found is that my printers are generally pretty consistent for dimensional accuracy -- my elegoo likes a tolerance of 0.05, but my Bambus like 0.04. YMMV. 

This relies on [Allerta Stencil](https://fonts.google.com/specimen/Allerta+Stencil) - a stencil font that is of course easy to install locally, but may not work at all on the Makerworld customizer. If you're okay with the centers of your letters falling out, this is still good. If you don't need labels, this is great - just leave the string empty.

# Printing recommendations

Layer height: 0.2 mm or 0.16 mm. Given the 1 mm wall thickness, this ensures 5–6 solid layers, which is critical for the structural integrity of the stencil bridges.

Print in PETG or above if you use your AMS heater. PLA might be fine in original AMS units. The labels are prone to stickage, so I've tried to rotate them to where my build plate is the flexiest, but an adhesion barrier might be worth doing if you're printing a bunch of them back to back.


```
outer_diameter=200
label_text = "Polymaker"; 
```
![Setting diameter to '200' and text to 'Polymaker'](https://github.com/user-attachments/assets/73a08202-f09b-49bf-972d-b5acf6731f03)

