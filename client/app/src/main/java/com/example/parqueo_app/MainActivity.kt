package com.example.parqueo_app

import android.graphics.ColorSpace.Rgb
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.colorspace.ColorSpaces
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.parqueo_app.ui.theme.Parqueo_appTheme
import android.os.Build
import androidx.core.view.WindowCompat
import androidx.compose.ui.graphics.RectangleShape
import androidx.compose.ui.graphics.Shape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import kotlinx.coroutines.delay


class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(
            window,
            false
        ) // Esto permite que tu app use toda la pantalla
        setContent {
            Parqueo_appTheme {
                Surface(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color.Black), // fondo negro total
                    color = Color.Black // opcional, asegura que sea fondo oscuro
                ) {
                    ParkCountContainer()
                }
            }
        }
    }

}

@Composable
fun ParkCountContainer() {
    var displayNumber by remember { mutableStateOf(1) }

    // Inicia un efecto que actualiza el número cada 500ms
    LaunchedEffect(Unit) {
        while (true) {
            displayNumber = (1..50).random()
            delay(500) // espera 0.5 segundos
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
            .padding(16.dp),
        contentAlignment = Alignment.Center
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .wrapContentHeight()
                .background(
                    brush = Brush.linearGradient(
                        listOf(Color(0xFFB9FBC0), Color(0xFF7CDEB0))
                    ),
                    shape = RoundedCornerShape(24.dp)
                )
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text("Parqueos FAI UPSA", fontSize = 30.sp, color = Color.Black)
            Text(displayNumber.toString(), fontSize = 120.sp, color = Color.Black)
        }
    }
}



@Composable
fun BDayGreeting(name: String, sender: String, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier.fillMaxSize(),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier
                .background(color = Color.Cyan)
                .padding(48.dp)
        ) {
            Text(
                text = "Hola $name, muchas felicidades en tu cumpleañosssss",
                fontSize = 36.sp,
                lineHeight = 44.sp,
                textAlign = TextAlign.Center,
            )
            Text(
                text = "Espero que tengas un día muy feliz, con mucho cariño, $sender",
                fontSize = 24.sp,
                textAlign = TextAlign.End,
                modifier = Modifier.padding(8.dp)
            )
        }
    }
}

@Composable
fun BdayImage(modifier: Modifier = Modifier) {
    val bdayImage = painterResource(R.drawable.androidparty)
    Box(modifier) {
        Image(
            painter = bdayImage,
            contentDescription = null,
            modifier = Modifier.fillMaxSize(),
            contentScale = ContentScale.Crop
        )
        BDayGreeting(
            "Mateo", "Emi", Modifier
                .fillMaxSize()
                .padding(8.dp)
        )
    }
}
