import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms'; // <-- NgModel lives here
import { HttpClientModule } from '@angular/common/http';

import { AppComponent } from './app.component';
import { ContractsComponent } from './contracts/contracts.component';
import { ContractDetailComponent } from './contract-detail/contract-detail.component';
import { MessagesComponent } from './messages/messages.component';
import { AppRoutingModule } from './app-routing.module';
import { DeployComponent } from './deploy/deploy.component';

@NgModule({
  declarations: [
    AppComponent,
    ContractsComponent,
    ContractDetailComponent,
    MessagesComponent,
    DeployComponent
  ],
  imports: [
    HttpClientModule,
    BrowserModule,
    FormsModule,
    AppRoutingModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }

