cd ibc-client
ng build --prod --build-optimizer --baseHref="/ibc/"
cd ..
cp ibc-client/dist/ibc-client/* ibc
mv ibc/index.html templates/.

