
icc = iccread('vg248qe-rtings-icc-profil.icm');

clut = table();
clut.red = icc.MatTRC.RedTRC;
clut.green = icc.MatTRC.GreenTRC;
clut.blue = icc.MatTRC.BlueTRC;

writetable(clut, 'asus-clut.csv');


rgb2xyz = table();
rgb2xyz.red = icc.MatTRC.RedTRC;
rgb2xyz.green = icc.MatTRC.GreenTRC;
rgb2xyz.blue = icc.MatTRC.BlueTRC;

writetable(rgb2xyz, 'asus-rgb2xyz.csv');
