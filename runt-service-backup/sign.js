const fs = require('fs');

// Esta funcion convierte de hexadecimal a base 64
function hexToBase64(str) {
    return Buffer.from(str.replace(/\s+/g, ''), 'hex').toString('base64');
}

try {
    // Cargar la librería jsrsasign
    const jsrsasignContent = fs.readFileSync('jsrsasign-js.txt', 'utf8');

    // Configurar el entorno
    var navigator = {};
    var window = {};

    // Cargar la librería
    eval(jsrsasignContent);

    // Leer la llave privada
    const llavepem = fs.readFileSync('claveprivada.pkcs8.pem', 'utf8');

    // Obtener los datos a firmar
    const dataToSign = process.argv[2];

    // Crear el objeto de llave
    const key = KEYUTIL.getKey(llavepem);

    // Configurar el algoritmo
    const sig = new KJUR.crypto.Signature({"alg": "SHA1withRSA"});

    // Inicializar con la llave
    sig.init(key);

    // Actualizar con los datos
    sig.updateString(dataToSign);

    // Firmar y obtener en hexadecimal
    const hSigVal = sig.sign();

    // Convertir a base64
    const base64 = hexToBase64(hSigVal);

    // Imprimir la firma
    console.log(base64);

} catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
}


