CREATE TABLE IF NOT EXISTS cliente(
    id_cliente serial, 
    nombre varchar(20) not null, 
    apellido varchar(20) not null, 
    telefono numeric(10,0), 
    direccion varchar(40) not null, 
    primary key (id_cliente)
);

CREATE TABLE IF NOT EXISTS sucursal(
    id_sucursal serial, 
    ubicacion varchar(20) not null, 
    cant_pasillos integer, 
    capacidad integer, 
    primary key (id_sucursal)
);

CREATE TABLE IF NOT EXISTS cliente_charcuteria(
    id_cliente serial, 
    no_fila integer, 
    id_sucursal integer,
    activada Boolean default False,
    primary key (id_cliente),
    foreign key (id_cliente) references cliente,
    foreign key (id_sucursal) references sucursal
);

CREATE TABLE IF NOT EXISTS factura(
    id_factura serial, 
    id_cliente serial, 
    fecha_hora timestamp default current_timestamp, 
    banco varchar(10) check (banco in ('Mercantil', 'Banesco', 'Provincial')), 
    id_sucursal integer,
    total numeric(8,0), 
    descuento numeric(8,0), 
    total_pago numeric(8,0), 
    primary key (id_factura), 
    foreign key (id_cliente) references cliente,
    foreign key (id_sucursal) references sucursal 
);

CREATE TABLE IF NOT EXISTS estante_inteligente(
    id_estante serial, 
    id_sucursal serial, 
    capacidad integer, 
    no_pasillo integer, 
    primary key (id_estante), 
    foreign key (id_sucursal) references sucursal
);

CREATE TABLE IF NOT EXISTS activacion_alarma(
    no_alarma serial, 
    id_estante serial, 
    fecha_hora timestamp default current_timestamp, 
    activada Boolean default False, 
    primary key (no_alarma), 
    foreign key (id_estante) references estante_inteligente
);

CREATE TABLE IF NOT EXISTS producto(
    id_producto serial,  
    nombre varchar(20) not null, 
    categoria varchar(20) not null,  
    primary key (id_producto)
);

CREATE TABLE IF NOT EXISTS inventario(
    id_producto integer, 
    fecha_hora timestamp default current_timestamp,  
    cantidad_inicial integer, 
    cantidad_restante integer,
    primary key (id_producto, fecha_hora), 
    foreign key (id_producto) references producto
);

CREATE TABLE IF NOT EXISTS producto_asignado(
    id_producto integer, 
    fecha_hora timestamp default current_timestamp,  
    id_estante integer,
    cantidad_inicial integer, 
    cantidad_restante integer,
    primary key (id_producto, fecha_hora), 
    foreign key (id_producto) references producto,
    foreign key (id_estante) references estante_inteligente
);

CREATE TABLE IF NOT EXISTS cambio_precio(
    fecha_hora timestamp default current_timestamp,
    id_producto integer, 
    precio numeric(8,0), 
    primary key (fecha_hora, id_producto), 
    foreign key (id_producto) references producto 
);

CREATE TABLE IF NOT EXISTS cuenta_programa_fidelidad(
    no_cuenta serial, 
    id_cliente serial, 
    fecha_suscripcion date default current_date, 
    fecha_finalizacion date default current_date+30, 
    foto varchar(50) default 'sin foto', 
    puntos integer not null default 0, 
    primary key (no_cuenta), 
    foreign key (id_cliente) references cliente
);

CREATE TABLE IF NOT EXISTS visita(
    no_visita serial, 
    no_cuenta serial, 
    id_cliente serial, 
    id_sucursal serial, 
    fecha_hora timestamp default current_timestamp, 
    primary key (no_visita), 
    foreign key (id_sucursal) references sucursal, 
    foreign key (no_cuenta) references cuenta_programa_fidelidad,
    foreign key (id_cliente) references cliente
);

CREATE TABLE IF NOT EXISTS detalle_factura(
    id_factura serial, 
    id_producto serial, 
    cantidad int,
    subtotal numeric(8,0),
    primary key (id_factura, id_producto), 
    foreign key (id_factura) references factura,
    foreign key (id_producto) references producto
);



