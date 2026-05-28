import http from 'k6/http';
import { sleep, check } from 'k6';

export let options = {
vus: 20, // usuarios virtuales
duration: '30s', // tiempo total de la prueba
};

export default function () {
http.get("http://127.0.0.1:8000/ping/");
sleep(1); // pausa de 1s entre peticiones
}

