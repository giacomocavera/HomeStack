const SERVICE_UUID = '000018f0-0000-1000-8000-00805f9b34fb';
const WRITE_CHAR_UUID = '00002af1-0000-1000-8000-00805f9b34fb';

let cachedDevice = null;
let writeCharacteristic = null;

async function getOrConnectDevice(blePrefixesStr) {
  if (cachedDevice && cachedDevice.gatt.connected && writeCharacteristic) {
    return writeCharacteristic;
  }

  const prefixes = (blePrefixesStr || 'FICHERO,D11')
    .split(',')
    .map((p) => p.trim())
    .filter(Boolean);

  let device = cachedDevice;

  if (!device && navigator.bluetooth.getDevices) {
    try {
      const pairedDevices = await navigator.bluetooth.getDevices();
      device = pairedDevices.find(
        (d) => d.name && prefixes.some((p) => d.name.startsWith(p))
      );
    } catch (e) {
      console.warn('Unable to query previously authorized devices:', e);
    }
  }

  if (!device) {
    const filters = prefixes.map((prefix) => ({ namePrefix: prefix }));
    const requestOptions = { optionalServices: [SERVICE_UUID] };

    if (filters.length > 0) {
      requestOptions.filters = filters;
    } else {
      requestOptions.acceptAllDevices = true;
    }

    device = await navigator.bluetooth.requestDevice(requestOptions);
  }

  const server = await device.gatt.connect();
  device.addEventListener('gattserverdisconnected', () => {
    writeCharacteristic = null;
  });

  const service = await server.getPrimaryService(SERVICE_UUID);
  writeCharacteristic = await service.getCharacteristic(WRITE_CHAR_UUID);
  cachedDevice = device;

  return writeCharacteristic;
}

function printViaBrowser(imageBase64, widthMm, heightMm) {
  return new Promise((resolve) => {
    const iframe = document.createElement('iframe');
    iframe.style.position = 'fixed';
    iframe.style.right = '0';
    iframe.style.bottom = '0';
    iframe.style.width = '0';
    iframe.style.height = '0';
    iframe.style.border = '0';
    document.body.appendChild(iframe);

    const doc = iframe.contentWindow.document;
    doc.open();
    doc.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Print Label</title>
          <style>
            @page {
              size: ${widthMm}mm ${heightMm}mm;
              margin: 0;
            }
            body {
              margin: 0;
              padding: 0;
              display: flex;
              align-items: center;
              justify-content: center;
            }
            img {
              width: ${widthMm}mm;
              height: ${heightMm}mm;
              display: block;
            }
          </style>
        </head>
        <body>
          <img src="${imageBase64}" onload="window.print();" />
        </body>
      </html>
    `);
    doc.close();

    setTimeout(() => {
      document.body.removeChild(iframe);
      resolve(true);
    }, 1200);
  });
}

export async function printLabel(payloadFetcher) {
  try {
    const res = await payloadFetcher();
    const data = res.data;

    if (data.transport === 'browser') {
      await printViaBrowser(data.image_base64, data.width_mm, data.height_mm);
      return true;
    }

    if (data.transport === 'network') {
      alert(data.message || 'Label sent to network printer successfully!');
      return true;
    }

    if (data.transport === 'ble') {
      if (!navigator.bluetooth) {
        alert('Web Bluetooth is not supported on this browser. Use Chrome, Edge or Chrome for Android.');
        return false;
      }

      const chunks = data.chunks;
      const writeChar = await getOrConnectDevice(data.ble_prefix);

      for (let i = 0; i < chunks.length; i++) {
        const binaryString = atob(chunks[i]);
        const bytes = new Uint8Array(binaryString.length);
        for (let j = 0; j < binaryString.length; j++) {
          bytes[j] = binaryString.charCodeAt(j);
        }

        if (writeChar.writeValueWithoutResponse) {
          await writeChar.writeValueWithoutResponse(bytes);
        } else {
          await writeChar.writeValue(bytes);
        }

        await new Promise((resolve) => setTimeout(resolve, 20));
      }

      return true;
    }

    return false;
  } catch (error) {
    cachedDevice = null;
    writeCharacteristic = null;
    
    if (error.name !== 'NotFoundError') {
      const errorMsg = error.response?.data?.detail || error.message;
      alert(`Print Error:\n${errorMsg}`);
    }
    return false;
  }
}