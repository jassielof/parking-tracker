package com.example.parqueo_app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.parqueo_app.ui.theme.Parqueo_appTheme
import androidx.core.view.WindowCompat
import androidx.compose.foundation.shape.RoundedCornerShape

// Importaciones de Retrofit, OkHttp y Gson
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import com.google.gson.annotations.SerializedName
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit

// Importaciones de ViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel // Para obtener el ViewModel en Compose
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch


// --- 1. Data Model ---
// Representa la estructura de la respuesta JSON del servidor
data class ParkingAvailabilityResponse(
    @SerializedName("available_spaces") val availableSpaces: Int,
    @SerializedName("total") val total: Int
)

// --- 2. API Service Interface (Retrofit) ---
// Define los endpoints de tu API
interface ParkingApiService {
    @GET("api/parking/availability")
    suspend fun getParkingAvailability(): ParkingAvailabilityResponse
}

// --- 3. Retrofit Client Configuration ---
// Objeto singleton para configurar y proporcionar la instancia de Retrofit
object RetrofitClient {
    // **IMPORTANTE:** Para el emulador, 10.0.2.2 es la IP para acceder a localhost de tu máquina.
    // Si estás en un dispositivo físico, usa la IP real de tu PC en la red local
    // (ej. "http://192.168.1.100:8000/").
    // Asegúrate de que tu servidor esté escuchando en esta IP y puerto.
    private const val BASE_URL = "http://10.0.2.2:8000/"

    // Interceptor para ver los logs de las solicitudes HTTP en Logcat
    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY // Nivel de detalle del log
    }

    // Cliente OkHttp con el interceptor de logging y timeouts
    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .connectTimeout(30, TimeUnit.SECONDS) // Tiempo de espera para la conexión
        .readTimeout(30, TimeUnit.SECONDS)    // Tiempo de espera para la lectura de la respuesta
        .build()

    // Instancia perezosa de ParkingApiService
    val instance: ParkingApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create()) // Usamos Gson para convertir JSON
            .build()
            .create(ParkingApiService::class.java)
    }
}

// --- 4. Repository Layer ---
// Clase que abstrae la fuente de datos (en este caso, la API)
class ParkingRepository(private val apiService: ParkingApiService) {
    suspend fun getParkingAvailability(): ParkingAvailabilityResponse {
        return apiService.getParkingAvailability()
    }
}

// --- 5. UI State ---
// Representa el estado de la UI que el ViewModel expone a los Composables
data class ParkingUiState(
    val availableSpaces: Int = 0,
    val totalSpaces: Int = 0,
    val isLoading: Boolean = true, // Para mostrar un indicador de carga
    val errorMessage: String? = null // Para mostrar mensajes de error
)

// --- 6. ViewModel ---
// ViewModel para gestionar la lógica de negocio y el estado de la UI
class ParkingViewModel(private val repository: ParkingRepository) : ViewModel() {

    // MutableStateFlow para el estado de la UI, privado para que solo el ViewModel lo modifique
    private val _uiState = MutableStateFlow(ParkingUiState())
    // StateFlow público para que los Composables lo observen
    val uiState: StateFlow<ParkingUiState> = _uiState.asStateFlow()

    init {
        // Inicia la recolección de datos cuando el ViewModel es creado
        collectParkingData()
    }

    private fun collectParkingData() {
        viewModelScope.launch {
            while (true) { // Bucle infinito para actualizar los datos periódicamente
                try {
                    // Restablece el estado de error antes de cada solicitud y activa la carga
                    // NOTA: isLoading se activa brevemente para mostrar el CircularProgressIndicator
                    // Si quieres evitar que el CircularProgressIndicator aparezca en actualizaciones rápidas,
                    // puedes añadir una lógica para que isLoading solo sea true si la consulta tarda más de un umbral.
                    _uiState.update { it.copy(errorMessage = null, isLoading = true) }

                    // Realiza la llamada a la API a través del repositorio
                    val response = repository.getParkingAvailability()

                    // Actualiza el estado de la UI con los nuevos datos
                    _uiState.update { currentState ->
                        currentState.copy(
                            availableSpaces = response.availableSpaces,
                            totalSpaces = response.total,
                            isLoading = false // Datos cargados
                        )
                    }
                } catch (e: Exception) {
                    // Manejo de errores
                    e.printStackTrace()
                    _uiState.update { currentState ->
                        currentState.copy(
                            isLoading = false, // Se detiene la carga, aunque haya error
                            errorMessage = "Error de red: ${e.message ?: "Desconocido"}. Reintentando..."
                        )
                    }
                }
                // Espera antes de la próxima solicitud (0.3 segundos)
                delay(300) // <-- CAMBIO AQUÍ: de 5000ms a 300ms
            }
        }
    }
}

// --- 7. ViewModel Factory ---
// Factoría para instanciar el ViewModel con el repositorio
class ParkingViewModelFactory(private val repository: ParkingRepository) : ViewModelProvider.Factory {
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(ParkingViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return ParkingViewModel(repository) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class")
    }
}

// --- 8. MainActivity and Composable UI ---
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Permite que la UI ocupe toda la pantalla, incluyendo la barra de estado
        WindowCompat.setDecorFitsSystemWindows(window, false)
        setContent {
            Parqueo_appTheme {
                Surface(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color.Black),
                    color = Color.Black
                ) {
                    // Crea una instancia del repositorio y la factoría del ViewModel
                    val repository = remember { ParkingRepository(RetrofitClient.instance) }
                    val viewModelFactory = remember { ParkingViewModelFactory(repository) }

                    // Obtiene la instancia del ViewModel. lifecycle-viewmodel-compose se encarga
                    // de mantener la instancia del ViewModel a través de cambios de configuración.
                    val parkingViewModel: ParkingViewModel = viewModel(factory = viewModelFactory)

                    ParkCountContainer(parkingViewModel)
                }
            }
        }
    }
}

@Composable
fun ParkCountContainer(viewModel: ParkingViewModel) {
    // Recopila el estado de la UI del ViewModel. Las recomposiciones se dispararán
    // automáticamente cuando el estado cambie.
    val uiState by viewModel.uiState.collectAsState()

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
            .padding(16.dp),
        contentAlignment = Alignment.Center
    ) {
        // --- CAMBIO CLAVE AQUÍ: Usamos un Card como contenedor estable para la tarjeta ---
        Card(
            shape = RoundedCornerShape(24.dp),
            // El color del contenedor de la tarjeta es transparente para que se vea el Brush
            colors = CardDefaults.cardColors(containerColor = Color.Transparent),
            modifier = Modifier
                .fillMaxWidth()
                .wrapContentHeight()
                .background( // Aplicamos el Brush directamente al Card
                    brush = Brush.linearGradient(
                        listOf(Color(0xFFB9FBC0), Color(0xFF7CDEB0))
                    ),
                    shape = RoundedCornerShape(24.dp) // La forma también va aquí
                )
                .padding(24.dp)
        ) {
            Column(
                modifier = Modifier.fillMaxWidth(), // La columna ahora llena el ancho del Card
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Text("Parqueos FAI UPSA", fontSize = 30.sp, color = Color.Black)

                // El contenido dinámico (carga, error, números) va dentro de esta Columna
                if (uiState.isLoading && uiState.availableSpaces == 0 && uiState.totalSpaces == 0) {
                    // Solo muestra el indicador de carga si los datos iniciales no están disponibles
                    CircularProgressIndicator(color = Color.Black)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("Cargando...", fontSize = 20.sp, color = Color.Black)
                } else if (uiState.errorMessage != null) {
                    // Muestra un mensaje de error si algo salió mal
                    Text(
                        "Error: ${uiState.errorMessage}",
                        fontSize = 18.sp,
                        color = Color.Red,
                        modifier = Modifier.fillMaxWidth(),
                        // Ya está centrado por la Column, no necesitamos textAlign aquí
                    )
                } else {
                    // Muestra los datos si se cargaron correctamente
                    // Estas Textos son los únicos que cambian su contenido
                    Text(uiState.availableSpaces.toString(), fontSize = 120.sp, color = Color.Black)
                    Text("/ ${uiState.totalSpaces}", fontSize = 24.sp, color = Color.Black)
                }
            }
        }
    }
}