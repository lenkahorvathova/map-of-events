DIR=/home/xbaisa/src/akce
cat vismo.ap.txt | parallel --tmpdir $DIR/data --files --col-sep ' ' python3 process.py {1} {2}
