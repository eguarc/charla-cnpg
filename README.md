# Lab Charla Nerdearla CNPG

[GIST](https://gist.github.com/eguarc/fe0752d141ef6e377b6d1331b8146251)

Al realizar el bootstrap del proyecto contenido en el directorio `dev/` con Flux CD, se obtendrá funcionando una aplicación básica, desarrollada en el framework Django para Python conectada a un cluster PostgreSQL de tres instancias. Todos los componentes quedarán funcionando sobre Kubernetes.

### Para acceder a la aplicación: 

```
kubectl port-forward -n app-nerdearla svc/app-nerdearla 8080:80
firefox localhost:8080
```

### Para acceder al dashboard de Grafana:

```
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 8000:80
firefox localhost:8000
```

