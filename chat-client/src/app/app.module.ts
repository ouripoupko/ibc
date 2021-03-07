import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms'; // <-- NgModel lives here
import { HttpClientModule } from '@angular/common/http';

import { AppComponent } from './app.component';
import { AppRoutingModule } from './app-routing.module';
import { ConnectComponent } from './connect/connect.component';
import { ChatpageComponent } from './chatpage/chatpage.component';

import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import { MatSliderModule } from '@angular/material/slider';

@NgModule({
  declarations: [
    AppComponent,
    ConnectComponent,
    ChatpageComponent
  ],
  imports: [
    HttpClientModule,
    FormsModule,
    BrowserModule,
    MatSliderModule,
    BrowserAnimationsModule,
    AppRoutingModule
  ],
  exports: [
    MatSliderModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
