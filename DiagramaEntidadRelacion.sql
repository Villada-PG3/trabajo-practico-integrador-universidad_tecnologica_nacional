CREATE DATABASE IF NOT EXISTS TrabajoIntegradorUTN;
USE TrabajoIntegradorUTN;

CREATE TABLE IF NOT EXISTS CARRERA (
    id_carrera INT AUTO_INCREMENT NOT NULL,
    nombre VARCHAR(100),
    sigla VARCHAR(100),
    PRIMARY KEY (id_carrera)
);

CREATE TABLE IF NOT EXISTS ALUMNO (
    id_alumno INT AUTO_INCREMENT NOT NULL,
    id_carrera INT,
    nombreCompleto VARCHAR(100),
    documento INT,
    email VARCHAR(100),
    PRIMARY KEY (id_alumno),
    CONSTRAINT FK_ALUMNO_ID_CARRERA FOREIGN KEY (id_carrera) REFERENCES CARRERA(id_carrera)
);

CREATE TABLE IF NOT EXISTS MATERIA (
    id_materia INT AUTO_INCREMENT NOT NULL,
    id_carrera INT,
    nombre VARCHAR(100),
    sigla VARCHAR(100),
    nivel INT,
    PRIMARY KEY (id_materia),
    CONSTRAINT FK_MATERIA_ID_CARRERA FOREIGN KEY (id_carrera) REFERENCES CARRERA(id_carrera)
);

CREATE TABLE IF NOT EXISTS TURNO (
    id_turno INT AUTO_INCREMENT NOT NULL,
    nombre VARCHAR(100),
    descripcion VARCHAR(100),
    PRIMARY KEY (id_turno)
);

CREATE TABLE IF NOT EXISTS CURSO (
    id_curso INT AUTO_INCREMENT NOT NULL,
    id_carrera INT,
    id_turno INT,
    nombre VARCHAR(100),
    nivel INT,
    PRIMARY KEY (id_curso),
    CONSTRAINT FK_CURSO_ID_CARRERA FOREIGN KEY (id_carrera) REFERENCES CARRERA(id_carrera),
    CONSTRAINT FK_CURSO_ID_TURNO FOREIGN KEY (id_turno) REFERENCES TURNO(id_turno)
);

CREATE TABLE IF NOT EXISTS CICLO_LECTIVO (
    id_ciclo_lectivo INT AUTO_INCREMENT NOT NULL,
    anio INT,
    descripcion VARCHAR(100),
    fechaInicio DATE,
    fechaFin DATE,
    PRIMARY KEY (id_ciclo_lectivo)
);

CREATE TABLE IF NOT EXISTS DICTADO_MATERIA (
    id_dictado_materia INT AUTO_INCREMENT NOT NULL,
    id_materia INT,
    id_curso INT,
    id_ciclo_lectivo INT,
    PRIMARY KEY (id_dictado_materia),
    CONSTRAINT FK_DICTADO_MATERIA_ID_MATERIA FOREIGN KEY (id_materia) REFERENCES MATERIA(id_materia),
    CONSTRAINT FK_DICTADO_MATERIA_ID_CURSO FOREIGN KEY (id_curso) REFERENCES CURSO(id_curso),
    CONSTRAINT FK_DICTADO_MATERIA_ID_CICLO_LECTIVO FOREIGN KEY (id_ciclo_lectivo) REFERENCES CICLO_LECTIVO(id_ciclo_lectivo)
);

CREATE TABLE IF NOT EXISTS HORARIO (
    id_horario INT AUTO_INCREMENT NOT NULL,
    id_dictado_materia INT,
    dia VARCHAR(100),
    PRIMARY KEY (id_horario),
    CONSTRAINT FK_HORARIO_ID_DICTADO_MATERIA FOREIGN KEY (id_dictado_materia) REFERENCES DICTADO_MATERIA(id_dictado_materia)
);

CREATE TABLE IF NOT EXISTS MODULO (
    id_modulo INT AUTO_INCREMENT NOT NULL,
    numero INT,
    horaInicio TIME,
    horaFin TIME,
    PRIMARY KEY (id_modulo)
);

CREATE TABLE IF NOT EXISTS HORARIO_MODULO (
    id_horario INT,
    id_modulo INT,
    CONSTRAINT FK_HORARIO_MODULO_ID_HORARIO FOREIGN KEY (id_horario) REFERENCES HORARIO(id_horario),
    CONSTRAINT FK_HORARIO_MODULO_ID_MODULO FOREIGN KEY (id_modulo) REFERENCES MODULO(id_modulo)
);

CREATE TABLE IF NOT EXISTS INSCRIPCION (
    id_inscripcion INT AUTO_INCREMENT NOT NULL,
    id_alumno INT,
    id_dictado_materia INT,
    codigoInscripcion VARCHAR(100),
    fechaInscripcion DATE,
    PRIMARY KEY (id_inscripcion),
    CONSTRAINT FK_INSCRIPCION_ID_ALUMNO FOREIGN KEY (id_alumno) REFERENCES ALUMNO(id_alumno),
    CONSTRAINT FK_INSCRIPCION_ID_DICTADO_MATERIA FOREIGN KEY (id_dictado_materia) REFERENCES DICTADO_MATERIA(id_dictado_materia)
);

CREATE TABLE IF NOT EXISTS CONDICION (
    id_condicion INT AUTO_INCREMENT NOT NULL,
    nombre VARCHAR(100),
    descripcion VARCHAR(100),
    esCondicionFinal BOOLEAN,
    PRIMARY KEY (id_condicion)
);

CREATE TABLE IF NOT EXISTS DOCENTE (
    id_docente INT AUTO_INCREMENT NOT NULL,
    legajo VARCHAR(100),
    nombre VARCHAR(100),
    apellido VARCHAR(100),
    PRIMARY KEY (id_docente)
);

CREATE TABLE IF NOT EXISTS CAMBIO_CONDICION (
    id_cambio_condicion INT AUTO_INCREMENT NOT NULL,
    id_inscripcion INT,
    id_condicion INT,
    id_docente INT,
    fechaHora DATETIME,
    PRIMARY KEY (id_cambio_condicion),
    CONSTRAINT FK_CAMBIO_CONDICION_ID_INSCRIPCION FOREIGN KEY (id_inscripcion) REFERENCES INSCRIPCION(id_inscripcion),
    CONSTRAINT FK_CAMBIO_CONDICION_ID_CONDICION FOREIGN KEY (id_condicion) REFERENCES CONDICION(id_condicion),
    CONSTRAINT FK_CAMBIO_CONDICION_ID_DOCENTE FOREIGN KEY (id_docente) REFERENCES DOCENTE(id_docente)
);

CREATE TABLE IF NOT EXISTS TIPO_EVALUACION (
    id_tipo_evaluacion INT AUTO_INCREMENT NOT NULL,
    nombre VARCHAR(100),
    descripcion VARCHAR(100),
    PRIMARY KEY (id_tipo_evaluacion)
);

CREATE TABLE IF NOT EXISTS EVALUACION (
    id_evaluacion INT AUTO_INCREMENT NOT NULL,
    id_inscripcion INT,
    id_tipo_evaluacion INT,
    id_docente INT,
    valor DECIMAL(10,2),
    fechaEvaluacion DATE,
    PRIMARY KEY (id_evaluacion),
    CONSTRAINT FK_EVALUACION_ID_INSCRIPCION FOREIGN KEY (id_inscripcion) REFERENCES INSCRIPCION(id_inscripcion),
    CONSTRAINT FK_EVALUACION_ID_TIPO_EVALUACION FOREIGN KEY (id_tipo_evaluacion) REFERENCES TIPO_EVALUACION(id_tipo_evaluacion),
    CONSTRAINT FK_EVALUACION_ID_DOCENTE FOREIGN KEY (id_docente) REFERENCES DOCENTE(id_docente)
);
