# Paraspool

A parametric rim adapter that is designed to be filament friendly, truly universal, and to accommodate any rim size you can think of that fits into an AMS (that part is your problem.) It works well with cardboard spools, but it might work with plastic spools as well (though I've personally never had any problems with plastic spools.)

It accepts a number of arguments, but the important ones are spool_diameter, tolerance, and label_text. What's worked well for me so far is just measuring the spool with a tape measure and then trying to print that exact number, then with a tolerance of 0.4. There are 'bundles' for known good values that have printed successfully, so in Customizers, you can just select (eg) "AICOPYTO" if you're using Aicopyto spools, and it should build a good part. What I have found is that my printers are generally pretty consistent for dimensional accuracy -- my elegoo likes a tolerance of 0.05, but my Bambus like 0.04. YMMV. 

The presets here for existing spools (like Polymaker, Inland, Elegoo, etc.) have been printed and tested to work, at least on my printer. 

This relies on [Allerta Stencil](https://fonts.google.com/specimen/Allerta+Stencil) - a stencil font that is of course easy to install locally, but may not work at all on the Makerworld customizer. If you're okay with the centers of your letters falling out, this is still good. If you don't need labels, this is great - just leave the string empty.

# Printing recommendations

Layer height: 0.2 mm or 0.16 mm. Given the 1 mm wall thickness, this ensures 5–6 solid layers, which is critical for the structural integrity of the stencil bridges.

Print in PETG or above if you use your AMS heater. PLA might be fine in original AMS units. The labels are prone to stickage, so I've tried to rotate them to where my build plate is the flexiest, but an adhesion barrier might be worth doing if you're printing a bunch of them back to back.


```
outer_diameter=200
label_text = "Polymaker"; 
```
![Setting diameter to '200' and text to 'Polymaker'](https://github.com/user-attachments/assets/73a08202-f09b-49bf-972d-b5acf6731f03)


## License

Just a small note on licensing, but while the software assets are MIT-licensed (as shown in the LICENSE.md,) the STL artifacts are released as CC-BY. That is of course reflected by the LICENSE.md in the `assets/` folder. I only note it here because it is not necessarily obvious to look in a subfolder for a separate license, but I understand this is common in open hardware projects (I'm a noob here.)

## ROADMAP

This isn't a roadmap so much as it is a braindump of things I'd like to do in the future. 

- I really want to incorporate the eSun cardboard spools, specifically because of [this project](https://makerworld.com/en/models/1234875-reusable-cardboard-spool-ams-lite-compatible?from=recommend#profileId-1254346)
- I understand that Polymaker has two sizes of spools. I've yet to encounter more than the one, which is covered, but I'd like to seek out the other.

## Coverage

This list is almost certainly not exhaustive, but it's every reputable brand I know about. Feel free to add a PR for any additional spools, *particularly* those that are cardboard. 

- [ ] 3DJake
- [x] AICOPYTO
- [ ] Anycubic
- [ ] Azurefilm
- [x] DEEPLEE
- [ ] Duramic
- [x] Elegoo
- [ ] Eryone
- [ ] eSun
- [ ] FormFutura
- [x] Inland
- [ ] Matter3D
- [x] Overture
- [x] Polymaker PanChroma / PolyTerra
- [ ] Polymaker PolyLite
- [ ] Polymaker PolyMax / PolySonic / Draft (I believe these are all the same spool)
- [ ] PrintedSolid
- [ ] ProtoPasta
