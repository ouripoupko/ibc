import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ChatpageComponent } from './chatpage/chatpage.component';

const routes: Routes = [
  { path: '', redirectTo: '/chatpage', pathMatch: 'full' },
  { path: 'chatpage/:name/:id', component: ChatpageComponent },
  { path: 'chatpage', component: ChatpageComponent }
];


@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
